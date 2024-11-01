from autoparadvisor_contrastive import *
import argparse
import pdb
import capnp

device = torch.device("cpu")
dtype = torch.float32

scallop_bounds = [{"name":"uniquely_mapped_only","type":"int","min":0,"max":1,"default":0,"hard_min":0,"hard_max":1},
                {"name":"use_second_alignment","type":"int","min":0,"max":1,"default":0,"hard_min":0,"hard_max":1},
                {"name":"max_dp_table_size","type":"int","min":0,"max":100000,"default":10000,"hard_min":0,"hard_max":float('inf')},
               {"name":"max_edit_distance","type":"int","min":0,"max":100,"default":10,"hard_min":0,"hard_max":float('inf')},
               {"name":"max_num_exons","type":"int","min":0,"max":10000,"default":1000,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_bundle_gap","type":"int","min":0,"max":500,"default":50,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_exon_length","type":"int","min":0,"max":200,"default":20,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_flank_length","type":"int","min":0,"max":30,"default":3,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_mapping_quality","type":"int","min":0,"max":10,"default":1,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_num_hits_in_bundle","type":"int","min":0,"max":200,"default":20,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_router_count","type":"int","min":0,"max":10,"default":1,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_splice_boundary_hits","type":"int","min":0,"max":10,"default":1,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_subregion_gap","type":"int","min":0,"max":30,"default":3,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_subregion_length","type":"int","min":0,"max":150,"default":15,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_transcript_length_base","type":"int","min":0,"max":1500,"default":150,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_transcript_length_increase","type":"int","min":0,"max":500,"default":50,"hard_min":0,"hard_max":float('inf')},
               {"name":"max_intron_contamination_coverage","type":"float","min":0.0,"max":20.0,"default":2.0,"hard_min":0,"hard_max":float('inf')},
               {"name":"min_subregion_overlap","type":"float","min":0.0,"max":15.0,"default":1.5,"hard_min":0,"hard_max":float('inf')}           
]

stringtie_bounds = [{"name":"t","type":"int","min":0,"max":1,"default":0,"hard_min":0,"hard_max":1},
                {"name":"u","type":"int","min":0,"max":1,"default":0,"hard_min":0,"hard_max":1},
                {"name":"m","type":"int","min":30,"max":2000,"default":200,"hard_min":30,"hard_max":float('inf')},
               {"name":"a","type":"int","min":0,"max":100,"default":10,"hard_min":0,"hard_max":float('inf')},
               {"name":"g","type":"int","min":0,"max":500,"default":50,"hard_min":0,"hard_max":float('inf')},
               {"name":"j","type":"float","min":0,"max":10,"default":1,"hard_min":0,"hard_max":float('inf')},
               {"name":"f","type":"float","min":0,"max":1,"default":0.01,"hard_min":0,"hard_max":1},
               {"name":"M","type":"float","min":0,"max":1,"default":1,"hard_min":0,"hard_max":1},         
]

parser = argparse.ArgumentParser('Advisor set generator')
parser.add_argument('--name', type=str)
parser.add_argument('--fastqs', nargs='+')
parser.add_argument('--assembler', type=str)
parser.add_argument('--top',type=int,default=5)
args = parser.parse_args()

fastq_files = args.fastqs
#print(fastq_files)
#pdb.set_trace()

print("Generating set representation of the new sample via MinHash sketch...")

'''
cmd = "cat "
for fastq_file in fastq_files:
    cmd += fastq_file + " "
cmd += "| mash sketch -r -m 2 -o "+args.name+" -"
print(cmd)
os.system(cmd)
'''

capnp.remove_import_hook()
mash_capnp = capnp.load("MinHash.capnp")
f_1 = open(args.name+".msh","rb")
read_mash = mash_capnp.MinHash.read(f_1)
hashes = list(read_mash.referenceListOld.references[0].hashes64)
counts = list(read_mash.referenceListOld.references[0].counts32)
assert len(hashes)==len(counts)
file_npy = np.array([hashes,counts])
#print(file_npy)
#print(file_npy.shape)
f_1.close()

normalization_params = np.load("zscore_params_"+args.assembler+".npy")

hash_mat = np.zeros((0,1000))
count_mat = np.zeros((0,1000))

hash_mat = np.vstack((hash_mat,file_npy[0]))
count_mat = np.vstack((count_mat,file_npy[1]))
normalized_vec = np.concatenate(((hash_mat-normalization_params[0,0])/normalization_params[0,1],(count_mat-normalization_params[1,0])/normalization_params[1,1]),axis=1)

print("Loading trained model...")
checkpoint = torch.load("trained_"+args.assembler+".pth",map_location=device)
model = Set_Encoder(r_dim=128,h1_dim=128,h2_dim=256,z_dim=64)
model.load_state_dict(checkpoint["model"])
model.to(device)
model.eval()

input_mash_mat_subsample_np = np.load("train_features_withaug_"+args.assembler+".npy")
input_mash_mat_subsample = torch.from_numpy(input_mash_mat_subsample_np).to(dtype=dtype,device=device)

data_size = int(input_mash_mat_subsample_np.shape[0]/8)
input_mash_mat_np = input_mash_mat_subsample_np[np.arange(data_size)*8+7]
input_mash_mat = torch.from_numpy(input_mash_mat_np).to(dtype=dtype,device=device)

representative_best_X = np.load("X_bests_"+args.assembler+".npy")

print("Finding nearest samples...")
sim_cal = torch.matmul(model(torch.from_numpy(normalized_vec).to(dtype=dtype,device=device)), model(input_mash_mat).T).detach().cpu().numpy()
#pdb.set_trace()

ind = np.argpartition(sim_cal[0], -args.top)[-args.top:]
ind = ind[np.argsort(sim_cal[0][ind])][::-1]
parameter_candidates = representative_best_X[ind]
#np.save("X_"+args.name+"_"+args.assembler+".npy",representative_best_X[ind])

print("Generating advisor set...")
cmd = "mkdir -p ./"+args.name+"_"+args.assembler+"_advisorset/"
os.system(cmd)
output_path = "./"+args.name+"_"+args.assembler+"_advisorset/"
for i in range(args.top):
    with open(output_path+"config_"+str(i+1),"wt")as f:
        fwriter = csv.writer(f,delimiter='\t')
        if args.assembler == "scallop":
            params = scallop_bounds
        else:
            params = stringtie_bounds
        for j in range(len(params)):
            if params[j]["type"]=="int":
                fwriter.writerow([params[j]["name"],int(parameter_candidates[i][j])])
            elif params[j]["type"]=="float":
                fwriter.writerow([params[j]["name"],float(parameter_candidates[i][j])])