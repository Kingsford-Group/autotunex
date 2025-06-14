To run paramters advised by DeBlasio et al. [2020], please see https://github.com/Kingsford-Group/scallopadvising.

To run BO on each RNA-seq sample, please see the instructions in the folder CAWarm-BO. 

To run AutoMash, first run mash sketch for each representative sample listed in representative_sample_scallop or representative_sample_stringtie, for example:

```bash
cat SRR3944332.fastq.gz | ./mash-Linux64-v2.3/mash sketch -r -m 2 -o SRR3944332 -
```
Next, for each query sample, also generate its MinHash sketch. Finally, run:

```bash
./mash-Linux64-v2.3/mash dist query.msh representative_R.msh
```
To compute the mash distance between the query sample and each representative sample. Pick top-k representative samples with smallest mash distances, and use their optimal parameter vectors. 

To run NAP, first install the package by following the instructions at https://github.com/huawei-noah/HEBO/tree/master/NAP. As no instructions are provided for applying NAP to a new case, we adapt their example to train and test NAP on our dataset using the following steps.

1. replace the source codes function_gym_nap.py and objectives.py with the new ones in the folder nap/. 
2. for each representative sample, fit its dats (X,Y) with Gaussian Process model. 
3. train nap with the script in the folder nap/. 
4. test with the script in the folder nap/. 

