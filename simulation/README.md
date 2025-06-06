We used CAMPAREE and BEERS2 to simulate raw FASTQ files. For installation instructions, please refer to their official repositories: https://github.com/itmat/CAMPAREE/tree/main and https://github.com/itmat/BEERS2/tree/main. 

The files ENCFF000CXQ.camparee.config.yaml and ENCFF000CXQ.beers2.config.yaml are example configuration templates used in our simulations. Please ensure to update the directory paths accordingly before using them. 

Here, we explain how to train our contrastive learning model. 

1. download all the files from https://doi.org/10.1184/R1/25037156.v1, here we need to use the following files:

   (1) sim_train_scallop.npy: the similarity matrix between samples in the representative set of Scallop, including all the samples from the data augmentation module.

   (2) sim_train_stringtie.npy: the similarity matrix between samples in the representative set of StringTie2, including all the samples from the data augmentation module.

   (3) train_features_withaug_scallop.npy: the set representations of all the samples in the representative set of Scallop, including all the samples from the data augmentation module.

   (4) train_features_withaug_stringtie.npy: the set representations of all the samples in the representative set of StringTie2, including all the samples from the data augmentation module.

2. Put all the files above and the scripts `autoparadvisor_train.py` and `autoparadvisor_contrastive.py` into the same folder, run the command:
```python
python autoparadvisor_train.py --assembler scallop
```
or
```python
python autoparadvisor_train.py --assembler stringtie
```

3. There are two output files:

   (1) scallop_trained_final.pth (
