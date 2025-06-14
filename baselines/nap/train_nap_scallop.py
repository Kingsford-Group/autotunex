import os
import multiprocessing as mp
import argparse

import sys
from pathlib import Path
import pdb
#root = str(Path(os.path.realpath(__file__)).parent.parent.parent)
#sys.path.insert(0, root)

#from nap.environment.hpo import get_hpo_specs, get_cond_hpo_specs
from nap.policies.transformer import generate_D_q_matrix

mp.set_start_method('spawn')

import torch
from datetime import datetime
from nap.RL.ppo_nap import PPO_NAP
from nap.policies.nap import NAP
from gym.envs.registration import register
import torch.distributed as dist
import botorch
from botorch.models import SingleTaskGP
from botorch.fit import fit_gpytorch_mll, fit_gpytorch_mll_torch
from gpytorch.mlls import ExactMarginalLogLikelihood
import pickle

from nap.RL.utils_gp import MixtureKernel

#torch.device('cuda:1')

ddp = False
if len(sys.argv) > 1:
    ddp = bool(sys.argv[1])

print("Enable DDP? ", ddp)
if ddp:
    dist.init_process_group("nccl")


dims = 18
num_dims = [i for i in range(2,18)]
cat_dims = [0,1]
num_classes = [2,2]
cat_alphabet = {0:[0,1],1:[0,1]}
na_dims = {}
nom_dims = []
points = 200
train_datasets = ["scallop_"+str(i)+".pkl" for i in range(0,1263)]
train_gp_models = ["scallop_"+str(i)+"_gp_model.pt" for i in range(0,1263)]

data_tmp = pickle.load(open(train_datasets[0], "rb"))
gp_tmp = torch.load(train_gp_models[0])
assert (data_tmp["domain"] == gp_tmp.train_inputs[0].cpu().numpy()).all()

env_spec = {
    "env_id": f"NAP-SLiidRL-MLP-CondP-v0",
    "f_type": "condscallop",
    "D": dims,
    "f_opts": {
        "min_regret": 1e-20,
        "models": train_gp_models,
        "data": train_datasets,
        "cat_dims": cat_dims,
        "cat_alphabet": cat_alphabet,
        "cat_alphabet_map": None,
        "cont_dims": num_dims,
        "na_dims": na_dims,
        "nom_dims": nom_dims,
        "X_mean": None,
        "X_std": None,
        # activate if condPrior
        "perturb_training_inputs": True,
        "num_dims_pert_dist": "unif",
        "num_dims_pert_dist_std": 0.1,
        "nb_perturbed_pos": 0,
        "normalize_X": True,
        # activate if not cond-prior
        "shuffle_and_cutoff": False,
        "y_row_sampling": False,
        "x_norm": False,
        "y_norm": False,
    },
    "features": ["incumbent", "timestep_perc"],
    "T": 24,
    "n_init_samples": 0,
    "pass_X_to_pi": False,
    "local_af_opt": False,
    "cardinality_domain": points,
    "reward_transformation": "neg_log10",  # true maximum not known
    "use_index_speedup": True,
}

low_memory = True
print("Low memory profile:", low_memory)

# specify PPO parameters
#n_iterations = args.iters
n_iterations = 2000
batch_size = 1440 // (dist.get_world_size() if ddp else 1)
n_workers = 5  # collecting workers per GPUs

y_range = (-0.1, 1.1)
print('y_range:', y_range)
arch_spec = dict(nbuckets=1000, dim_feedforward=1024, emb_size=512, nlayers=6, nhead=4, dropout=0.0,
                    temperature=0.1, y_range=y_range,
                    af_name="mlp" if "MLP" in env_spec["env_id"] else ("ucb" if "UCB" in env_spec["env_id"] else "ei"),
                    joint_model_af_training=False if "Disjoint" in env_spec["env_id"] else True,
                    )

ppo_spec = {
    "batch_size": batch_size,
    "max_steps": n_iterations * batch_size,
    "minibatch_size": 16 if not low_memory else 8,
    "grad_accumulation": 2 if not low_memory else 4,
    "n_epochs": 1,
    "lr": 3e-5,
    "epsilon": 0.15,
    "ppo_coeff": 1.0 if "RL" in env_spec["env_id"] else 0.0,  # 1.0 = SL+RL / 0.0 = SL+BO-like
    "value_coeff": 1.0,
    "ent_coeff": 0.001 if "EntReg" in env_spec["env_id"] else 0.0,
    "ce_coeff": 1.0,

    "SL_iid": "iid" in env_spec["env_id"],
    "SL_iid_fast": True,

    "decay_lr": True,
    "gamma": 0.98,
    "lambda": 0.98,
    "grad_clip": 0.5,
    "loss_type": "GAElam",
    "normalize_advs": True,
    "n_workers": n_workers,
    "env_id": env_spec["env_id"],
    "seed": 0,
    "argmax": False,
    "env_seeds": list(range(n_workers)),
    "policy_options": {
        "max_query": env_spec["cardinality_domain"],
        "arch_spec": arch_spec,
        "use_value_network": True,
        "arch_spec_value": arch_spec
    },
    "covar_reg_dict": {
        "coeff": 1.0 if "KL" in env_spec["env_id"] else 0.0,
        "x_dist": "inf",
        "hist_dist": "kl",
        "eps": 0.1,
    },
}

register(
    id=env_spec["env_id"],
    entry_point="nap.environment.function_gym_nap:NAPEnv",
    max_episode_steps=env_spec["T"],
    reward_threshold=None,
    kwargs=env_spec
)

logpath = os.path.join("./HEBO/NAP/", "log/TRAIN", "scallop", env_spec["env_id"], datetime.strftime(datetime.now(), "%Y-%m-%d-%H-%M-%S"))

if env_spec["f_opts"].get("shuffle_and_cutoff", False) or env_spec["f_type"] in ["condHPO", "HPO", "condstringtie", "condscallop"]:
    # pre-compute masks for computational gain
    policy_net_masks = []
    for i in range(env_spec["T"]):
        policy_net_masks.append(
            generate_D_q_matrix(env_spec["T"] + env_spec["cardinality_domain"] + env_spec["n_init_samples"],
                                env_spec["n_init_samples"] + i))
    policy_net_masks = torch.stack(policy_net_masks)
else:
    # we have datasets of different sizes, so we can't pre-compute masks using env_spec["cardinality_domain"].
    # We set them to None and will let the forward pass figure out their shapes
    policy_net_masks = None

# set up policy
policy_fn = lambda observation_space, action_space, deterministic, dataparallel: NAP(
    observation_space=observation_space,
    action_space=action_space,
    deterministic=True if ppo_spec["argmax"] else deterministic,
    options=ppo_spec["policy_options"],
    dataparallel=dataparallel,
    policy_net_masks=policy_net_masks,
    mixed_type_options={
        "cat_dims": env_spec["f_opts"]["cat_dims"],
        "num_dims": env_spec["f_opts"]["cont_dims"],
        "cat_alphabet": env_spec["f_opts"]["cat_alphabet"],
        "cat_alphabet_map": env_spec["f_opts"]["cat_alphabet_map"],
        "mixed_type": "MixNAP" in env_spec["env_id"],
    },
)

# do training
if not ddp or dist.get_rank() == 0:
    print("Training on {}.\nFind logs, weights, and learning curve at {}\n\n".format(env_spec["env_id"], logpath))

ppo = PPO_NAP(policy_fn=policy_fn, params=ppo_spec, logpath=logpath, save_interval=10)
ppo.train()
