For running paramters advised by DeBlasio et al. [2020], please see https://github.com/Kingsford-Group/scallopadvising.

For running BO on each RNA-seq sample, please see the instructions in the folder CAWarm-BO. 

For running AutoMash, first run mash sketch for each representative sample listed in representative_sample_scallop or representative_sample_stringtie, for example:

```bash
cat SRR3944332.fastq.gz | ./mash-Linux64-v2.3/mash sketch -r -m 2 -o SRR3944332 -
```
Next, for each query sample, also generate its MinHash sketch. Finally, run:

```bash
./mash-Linux64-v2.3/mash dist query.msh representative_R.msh
```
To compute the mash distance between the query sample and each representative sample. Pick top-k representative samples with smallest mash distances, and use their optimal parameter vectors. 

We used CAMPAREE and BEERS2 to simulate raw FASTQ files. For installation instructions, please refer to their official repositories: https://github.com/itmat/CAMPAREE/tree/main and https://github.com/itmat/BEERS2/tree/main. 

The files ENCFF000CXQ.camparee.config.yaml and ENCFF000CXQ.beers2.config.yaml are example configuration templates used in our simulations. Please ensure to update the directory paths accordingly before using them. 

