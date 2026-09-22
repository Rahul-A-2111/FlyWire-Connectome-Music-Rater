import os
import numpy as np
import pandas as pd
import scipy.sparse as sp
from caveclient import CAVEclient

# ==========================================
# 1. CONNECT TO FLYWIRE FAFB DATASET
# ==========================================
DATASTACK_NAME = 'flywire_fafb_public'
SYNAPSE_FILE = "jon_synapses.csv"

print(f"Connecting to CAVEclient dataset: {DATASTACK_NAME}...")
client = CAVEclient(DATASTACK_NAME)

# ==========================================
# 2. FETCH OR LOAD SYNAPTIC DATA
# ==========================================
if not os.path.exists(SYNAPSE_FILE):
    print("Fetching auditory sensory neurons (JONs) from FlyWire...")
    annotations = client.materialize.query_table('hierarchical_neuron_annotations')
    
    # Filter for Johnston's Organ Neurons (JONs)
    jon_mask = annotations['cell_type'].astype(str).str.contains('JON|JO-', case=False, na=False)
    jons = annotations[jon_mask]
    jon_ids = jons['pt_root_id'].unique().tolist()
    print(f"Found {len(jon_ids)} Johnston's Organ (JON) auditory neurons.")

    print("Querying downstream synapses from FlyWire database...")
    # Fetch synapses for the first 50 JONs to keep the simulation matrix lightweight
    synapses = client.materialize.query_table(
        'synapses_nt_v1',
        filter_in_dict={'pre_pt_root_id': jon_ids[:50]}
    )
    
    # Save to local CSV file
    synapses.to_csv(SYNAPSE_FILE, index=False)
    print(f"Saved {len(synapses)} raw synapses to '{SYNAPSE_FILE}'.")
else:
    print(f"Loading cached synapses from '{SYNAPSE_FILE}'...")
    synapses = pd.read_csv(SYNAPSE_FILE)

# ==========================================
# 3. CONSTRUCT CONNECTIVITY MATRIX
# ==========================================
# Group pre/post neuron pairs to get synaptic contact count
syn_counts = synapses.groupby(['pre_pt_root_id', 'post_pt_root_id']).size().reset_index(name='synapse_count')

# Filter for strong connections (>= 3 synapses) to filter background noise
strong_connections = syn_counts[syn_counts['synapse_count'] >= 3].copy()

# Map neuron IDs to 0-indexed matrix indices
all_neurons = sorted(list(set(strong_connections['pre_pt_root_id']).union(set(strong_connections['post_pt_root_id']))))
neuron_to_idx = {nid: i for i, nid in enumerate(all_neurons)}
num_neurons = len(all_neurons)

rows = strong_connections['pre_pt_root_id'].map(neuron_to_idx).values
cols = strong_connections['post_pt_root_id'].map(neuron_to_idx).values
weights = strong_connections['synapse_count'].values

# Create sparse CSR matrix
adj_matrix = sp.csr_matrix((weights, (rows, cols)), shape=(num_neurons, num_neurons))

# Determine input indices for JON sensory neurons
presynaptic_jons = set(strong_connections['pre_pt_root_id'])
input_indices = [neuron_to_idx[nid] for nid in presynaptic_jons if nid in neuron_to_idx]

# ==========================================
# 4. LEAKY INTEGRATE-AND-FIRE (LIF) SIMULATOR
# ==========================================
class FlyAuditoryNetwork:
    def __init__(self, W, tau_m=10.0, v_thresh=-50.0, v_reset=-65.0):
        self.W = W.toarray()  # Matrix representation (N x N)
        self.N = W.shape[0]
        self.tau_m = tau_m
        self.v_thresh = v_thresh
        self.v_reset = v_reset

    def run_simulation(self, input_currents, dt=0.1):
        num_steps = input_currents.shape[0]
        V = np.full((self.N,), self.v_reset)
        spike_record = []

        for t in range(num_steps):
            # Inject audio driving current into sensory input neurons
            I_ext = np.zeros(self.N)
            if len(input_indices) > 0:
                I_ext[input_indices] = input_currents[t]
            
            # Membrane potential update step
            dV = (-(V - self.v_reset) + I_ext) / self.tau_m * dt
            V += dV

            # Detect threshold crossing and record spikes
            spikes = V >= self.v_thresh
            V[spikes] = self.v_reset
            spike_record.append(spikes)

            # Recurrent synaptic input to downstream neurons for next step
            synaptic_input = np.dot(spikes.astype(float), self.W)
            V += synaptic_input * 2.0  # Synaptic weight gain

        return np.array(spike_record)

if __name__ == '__main__':
    print(f"Connectome setup ready with {num_neurons} neurons and {len(strong_connections)} connections.")