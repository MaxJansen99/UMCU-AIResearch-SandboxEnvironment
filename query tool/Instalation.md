# Installation
We used a conda to manage our environment but if you want to use somthing else that is up to you, a base environment should also work. Below is the process we followed to create our environment

## Conda environmet
We start with creating a new conda environment, 
if you do not have conda you can dowload it from the [official website](https://docs.anaconda.com/miniconda/) and follow the installation steps there.
Once you are ready to create the environment use the code below to create and activate the environment.

Run the following code in `Anaconda Prompt` on Windows and in `Terminal` on Macbook/Linux
```bash
conda create -n imagine-query -y
conda activate imagine-query
```

## Package installation 
To install all the required packages you should first clone this repository.
```bash
git clone https://github.com/MaxJansen99/UMCU-AIResearch-SandboxEnvironment.git
```
Then install the required packages from the `requirements.txt` file. Make sure to execute this command from inside the repository
```bash
pip install -r query/requirements.txt
```

## Launch
You are now ready to use the environment and therefore the code in this repository.
