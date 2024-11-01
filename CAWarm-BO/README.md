# CAWarm-BO

Here we describe the way to run CAWarm-BO on RNA-seq samples. 

## Installation 

The codes here heavily depend on the codes in https://github.com/xingchenwan/Casmopolitan. Therefore, please follow their documents for installing the required packages. 

In addition, we need to install the following packages and softwares: 

1. PyYAML, `pip install PyYAML`
2. Transcript assemblers such as Scallop (https://github.com/Kingsford-Group/scallop) and StringTie (https://ccb.jhu.edu/software/stringtie/).
3. gffcompare: https://github.com/gpertea/gffcompare
4. gtfcuff: https://github.com/Kingsford-Group/rnaseqtools

## Set YAML config 

First, download a gene annotation file (.gtf), e.g. https://www.gencodegenes.org/human/release_24.html. This file is for computing AUC values. 

Second, change the information in .yml file if needed. We have provided three YAML files for Scallop, Scallop2 (https://github.com/Shao-Group/scallop2), and StringTie, but one can also create new .yml for other softwares. 

Take scallop.yml as an example, there are several places that users might need to change:

1. the path of the transcript assembler (testing_software -> path)
2. additional options for running transcript assemblers (testing_software -> additional_option), e.g. if the library type of the RNA-seq sample input is "first", then add `--library_type first` to the additional option.
3. parameter information (parameter_bounds)
4. the path of gffcompare (evaluation-> the first 'path')
5. the path of the gene annotation file (evaluation-> ref_file)
6. the path of gtfcuff (evaluation-> the second 'path')
7. the number of transcripts in the gene annotation file (evaluation-> transcript_num), you can obtain this value via the command `cat annotation.gtf | awk '{print $3}' | grep -c transcript`, this value will only affect the scale of the AUC values. 

## Run CAWarm-BO

To run CAWarm-BO on a RNA-seq sample e.g. accesion number: SRR307903, 

1. Download .fastq files from SRA.
2. Use RNA-seq aligner, such as STAR (https://github.com/alexdobin/STAR) to do the alignment, and sort the alignment output by coordinate, generating the bam file, e.g. SRR307903.bam.
3. Run CAWarm-BO via the command `python main.py -p scallop --max_iters 200 --save_path SRR307903_scallop --input_file SRR307903.bam --cawarmup 60 --ard -a thompson --config_file scallop.yml` (or `python main.py -p stringtie --max_iters 200 --save_path SRR307903_stringtie --input_file SRR307903.bam --cawarmup 60 --ard -a thompson --config_file stringtie.yml`). The results will be stored in the folder SRR307903_scallop/. There are three output files:

   (1) wall_clock.npy: the wall clock time for each iteration.

   (2) X.npy: the queried parameter vector for each iteration. 

   (3) Y.npy: the negative AUC values (*10^4) for each iteration. 

CAWarm-BO supports the following parameters:
| Parameter       | Default Value | Description                                                                                                 |
|-----------------|---------------|-------------------------------------------------------------------------------------------------------------|
| -p              | scallop          | The name of the TranscriptAssembler                                                             |
| --max_iters     | 150           | Maximum number of BO iterations                                                                             |
| --n_trials      | 1            | Number of trials for the experiment                                                                         |
| --n_init        | 10            | Number of initialising random points                                                                        |
| --save_path     | output/       | save directory                                                                            |
| --cawarmup      | 0             | number of iterations for coordinating ascent to warm up the process                                                     |
| --ard           |               | whether to enable automatic relevance determination                                           |
| -a              | thompson      | choice of the acquisition function among ucb, ei, thompson, please use thompson if there are integer valuables.                                                |
| --input_file    | None          | The path of input file/files of software                                                                    |
| --param_type    | mixed         | choice of parameter type among category or continuous or mixed                                              |
| --config_file | scallop.yml     | The path for yaml config file        
