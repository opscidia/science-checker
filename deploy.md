# Deploying scita to production on an AWS EC2 instance or on a local server

For an installation on EC2, it is assumed that the instance is already created. 

## Prerequisite

Install docker and git packages.

```bash
sudo apt install -y docker git
```

## 1- Clone sources from github

```bash
git clone https://github.com/opscidia/FullTextDataProject.git scita
```

* For using dev branch

```bash
git clone -b dev https://github.com/opscidia/FullTextDataProject.git scita_demo
```

---
**IMPORTANT**

After having clone, you have to define the AWS keys and AUTH0 values respectively in *env.prod* and  *visualization/.Renviron.TEMPLATE* 

## 2- Deploy containers

* Use the following command to deploy the container images:

```bash
cd sripts_docker
./deploy_containers.sh
```

* Copy all models that the API needs into *data/model/prod/*

## 3- Run the containers

```bash
./run_containers.sh
```

