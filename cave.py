import os
import numpy as np
import pandas as pd
import scipy.sparse as sp
from caveclient import CAVEclient

# ==========================================
# 1. CONNECT TO FLYWIRE FAFB DATASET
# ==========================================
DATASTACK_NAME = 'flywire_fafb_public'
ANNOTATION_FILE = "neuron_annotations.csv"
SYNAPSE_FILE = "jon_synapses.csv"

# --- Circuit-specific JON cell-type patterns (regex, case-insensitive) ---
JON_AB_PATTERN = 'JON-A|JON-B'   # near-field courtship / low-freq particle velocity
JON_CE_PATTERN = 'JON-C|JON-E'   # wind / gravity / high-intensity threat transients
JON_ANY_PATTERN = 'JON|JO-'      # fallback catch-all for unclassified JONs

# --- Downstream neuropils / cell types traced for scoring ---
DOWNSTREAM_TARGETS = {
    'AMMC':  'AMMC',              # Antennal Motor & Mechanosensory Center: raw sensory fidelity
    'P1':    'P1',                # Central complex mating-decision neurons
    'pIP10': 'pIP10',             # Descending courtship-song command neurons
    'LC4':   'LC4',               # Visual/escape looming-detector, feeds Giant Fiber
    'GF':    'Giant Fiber',       # Giant Fiber escape circuit -- threat/swatter response
    'PAM':   'PAM',               # Dopaminergic mushroom-body reward cluster
}

print(f"Connecting to CAVEclient dataset: {DATASTACK_NAME}...")
client = CAVEclient(DATASTACK_NAME)

# ==========================================
# 2. FETCH OR LOAD ANNOTATIONS
# ==========================================
if not os.path.exists(ANNOTATION_FILE):
    print("Fetching neuron annotations from FlyWire...")
    annotations = client.materialize.query_table('hierarchical_neuron_annotations')
    annotations.to_csv(ANNOTATION_FILE, index=False)
else:
    print(f"Loading cached annotations from '{ANNOTATION_FILE}'...")
    annotations = pd.read_csv(ANNOTATION_FILE)

annotations['cell_type'] = annotations['cell_type'].astype(str)

# ==========================================
# 3. CIRCUIT-SPECIFIC JON FILTERING
# ==========================================
jon_ab_mask = annotations['cell_type'].str.contains(JON_AB_PATTERN, case=False, na=False, regex=True)
jon_ce_mask = annotations['cell_type'].str.contains(JON_CE_PATTERN, case=False, na=False, regex=True)
jon_other_mask = (
    annotations['cell_type'].str.contains(JON_ANY_PATTERN, case=False, na=False, regex=True)
    & ~jon_ab_mask & ~jon_ce_mask
)

jon_ab_ids = annotations.loc[jon_ab_mask, 'pt_root_id'].unique().tolist()
jon_ce_ids = annotations.loc[jon_ce_mask, 'pt_root_id'].unique().tolist()
jon_other_ids = annotations.loc[jon_other_mask, 'pt_root_id'].unique().tolist()
all_jon_ids = jon_ab_ids + jon_ce_ids + jon_other_ids

print(f"Found {len(jon_ab_ids)} JON-A/B (courtship channel), "
      f"{len(jon_ce_ids)} JON-C/E (wind/threat channel), "
      f"{len(jon_other_ids)} unclassified JON neurons.")

# ==========================================
# 4. FETCH OR LOAD SYNAPTIC DATA
# ==========================================
if not os.path.exists(SYNAPSE_FILE):
    print("Querying downstream synapses from FlyWire database...")
    # Cap the seed set to keep the simulation matrix lightweight
    synapses = client.materialize.query_table(
        'synapses_nt_v1',
        filter_in_dict={'pre_pt_root_id': all_jon_ids[:100]}
    )
    synapses.to_csv(SYNAPSE_FILE, index=False)
    print(f"Saved {len(synapses)} raw synapses to '{SYNAPSE_FILE}'.")
else:
    print(f"Loading cached synapses from '{SYNAPSE_FILE}'...")
    synapses = pd.read_csv(SYNAPSE_FILE)

if 'neurotransmitter_type' not in synapses.columns:
    synapses['neurotransmitter_type'] = 'unknown'


def _sign_for_neurotransmitter(nt):
    """GABAergic and glutamatergic synapses are treated as inhibitory."""
    nt = str(nt).lower()
    if 'gaba' in nt or 'glutamate' in nt:
        return -1.0
    return 1.0


synapses['sign'] = synapses['neurotransmitter_type'].apply(_sign_for_neurotransmitter)

# ==========================================
# 5. CONSTRUCT SIGNED CONNECTIVITY MATRIX
# ==========================================
syn_grouped = synapses.groupby(['pre_pt_root_id', 'post_pt_root_id']).agg(
    synapse_count=('post_pt_root_id', 'size'),
    sign=('sign', lambda s: s.mode().iat[0] if len(s.mode()) else 1.0)
).reset_index()

# Filter for strong connections (>= 3 synapses) to suppress background noise
strong_connections = syn_grouped[syn_grouped['synapse_count'] >= 3].copy()
strong_connections['signed_weight'] = strong_connections['synapse_count'] * strong_connections['sign']

all_neurons = sorted(list(
    set(strong_connections['pre_pt_root_id']).union(set(strong_connections['post_pt_root_id']))
))
neuron_to_idx = {nid: i for i, nid in enumerate(all_neurons)}
num_neurons = len(all_neurons)

rows = strong_connections['pre_pt_root_id'].map(neuron_to_idx).values
cols = strong_connections['post_pt_root_id'].map(neuron_to_idx).values
weights = strong_connections['signed_weight'].values

# Signed sparse matrix: positive = excitatory (ACh), negative = inhibitory (GABA/Glu)
adj_matrix = sp.csr_matrix((weights, (rows, cols)), shape=(num_neurons, num_neurons))

# Input indices, split by acoustic channel
jon_ab_indices = [neuron_to_idx[nid] for nid in jon_ab_ids if nid in neuron_to_idx]
jon_ce_indices = [neuron_to_idx[nid] for nid in jon_ce_ids if nid in neuron_to_idx]
jon_other_indices = [neuron_to_idx[nid] for nid in jon_other_ids if nid in neuron_to_idx]
# Kept for backward compatibility with callers expecting one combined list
input_indices = sorted(set(jon_ab_indices) | set(jon_ce_indices) | set(jon_other_indices))

# ==========================================
# 6. DOWNSTREAM NEUROPIL / CELL-TYPE INDEX MAP
# ==========================================
def _indices_for_pattern(pattern):
    mask = annotations['cell_type'].str.contains(pattern, case=False, na=False, regex=True)
    ids = annotations.loc[mask, 'pt_root_id'].unique().tolist()
    return [neuron_to_idx[nid] for nid in ids if nid in neuron_to_idx]


downstream_indices = {name: _indices_for_pattern(pattern) for name, pattern in DOWNSTREAM_TARGETS.items()}
for name, idxs in downstream_indices.items():
    print(f"  Downstream region '{name}': {len(idxs)} neurons mapped in network.")


# ==========================================
# 7. LEAKY INTEGRATE-AND-FIRE (LIF) SIMULATOR
#    -- inhibitory synapses, refractory periods, synaptic depression --
# ==========================================
class FlyAuditoryNetwork:
    def __init__(self, W, tau_m=10.0, v_thresh=-50.0, v_reset=-65.0,
                 refractory_ms=2.5, tau_depression=200.0, depression_recovery=0.02):
        """
        W: signed connectivity matrix (scipy sparse or ndarray). Positive
           entries are excitatory (acetylcholine), negative entries are
           inhibitory (GABA/glutamate), as tagged upstream from FlyWire's
           neurotransmitter predictions.
        refractory_ms: absolute refractory period per neuron (~300 Hz firing cap).
        tau_depression: time constant (ms) governing how fast a synapse
           depletes with repeated use ("boredom" on repetitive loops).
        depression_recovery: per-ms recovery rate back toward full efficacy at rest.
        """
        self.W = W.toarray() if sp.issparse(W) else np.asarray(W)
        self.N = self.W.shape[0]
        self.tau_m = tau_m
        self.v_thresh = v_thresh
        self.v_reset = v_reset
        self.refractory_ms = refractory_ms
        self.tau_depression = tau_depression
        self.depression_recovery = depression_recovery

    def run_simulation(self, input_currents_by_channel, input_indices_by_channel, dt=0.1):
        """
        input_currents_by_channel: dict {channel_name: ndarray[T]} -- e.g.
            {'JON_AB': env_ab, 'JON_CE': env_ce} from audio_utils.wav_to_jon_current
        input_indices_by_channel: dict {channel_name: list[int]} -- matrix
            indices each channel's current should be injected into (e.g.
            jon_ab_indices, jon_ce_indices from this module).

        Returns spike_record: ndarray[T, N] boolean.
        """
        num_steps = max((len(arr) for arr in input_currents_by_channel.values()), default=0)
        V = np.full((self.N,), self.v_reset)
        refractory_timer = np.zeros(self.N)     # ms remaining before a neuron can fire again
        synaptic_efficacy = np.ones(self.N)     # 1.0 = fresh; decays toward 0 with fatigue
        spike_record = []

        for t in range(num_steps):
            I_ext = np.zeros(self.N)
            for channel, currents in input_currents_by_channel.items():
                idxs = input_indices_by_channel.get(channel, [])
                if len(idxs) > 0 and t < len(currents):
                    I_ext[idxs] += currents[t]

            not_refractory = refractory_timer <= 0

            # Membrane potential update -- neurons in their refractory window don't integrate
            dV = (-(V - self.v_reset) + I_ext) / self.tau_m * dt
            V[not_refractory] += dV[not_refractory]

            spikes = (V >= self.v_thresh) & not_refractory
            V[spikes] = self.v_reset
            refractory_timer[spikes] = self.refractory_ms
            spike_record.append(spikes)

            # Recurrent synaptic input, scaled by each neuron's current efficacy (fatigue),
            # and signed by W so GABAergic/glutamatergic connections inhibit downstream cells.
            effective_spikes = spikes.astype(float) * synaptic_efficacy
            synaptic_input = np.dot(effective_spikes, self.W)
            V[not_refractory] += synaptic_input[not_refractory] * 2.0

            # Synaptic depression: neurons that just fired deplete their output efficacy;
            # everything slowly recovers toward full strength at rest ("boredom" recovers
            # between repetitive stimuli, desensitizes during them).
            synaptic_efficacy[spikes] *= np.exp(-dt / self.tau_depression)
            synaptic_efficacy += (1.0 - synaptic_efficacy) * self.depression_recovery
            synaptic_efficacy = np.clip(synaptic_efficacy, 0.05, 1.0)

            refractory_timer = np.maximum(refractory_timer - dt, 0.0)

        return np.array(spike_record)

    @staticmethod
    def region_firing_rate(spike_record, indices, dt=0.1):
        """Mean per-neuron firing rate (Hz) across a downstream region over the run."""
        if len(indices) == 0 or spike_record.size == 0:
            return 0.0
        duration_s = spike_record.shape[0] * dt / 1000.0
        if duration_s <= 0:
            return 0.0
        total_spikes = spike_record[:, indices].sum()
        return float(total_spikes / len(indices) / duration_s)


if __name__ == '__main__':
    print(f"Connectome setup ready with {num_neurons} neurons and {len(strong_connections)} connections.")
    print(f"JON-A/B input neurons in network: {len(jon_ab_indices)}")
    print(f"JON-C/E input neurons in network: {len(jon_ce_indices)}")
    for name, idxs in downstream_indices.items():
        print(f"{name}: {len(idxs)} neurons")