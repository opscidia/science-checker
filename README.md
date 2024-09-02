<!-- @copyright  Copyright (c) 2018-2024 Opscidia -->
# Science Checker

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=Python&logoColor=f1c40f)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-engine-2496ED?style=for-the-badge&logo=docker)](https://www.djangoproject.com/download/)

</div>

Code implementation of [Science Checker Reloaded](https://arxiv.org/abs/2402.13897).

To access the [Extractive-Boolean QA For Scientific Fact Checking](https://doi.org/10.1145/3512732.3533580) code implementation, please refer to the [v1.0 branch](https://github.com/opscidia/science-checker/releases/tag/v1.0).


## Installation
Install Docker and Docker Compose if you haven't already.  
Then, run the following commands to build the Docker image.

```sh
docker-compose build
```

Download the entity-fishing models.
```sh
wget -qO- https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-kb.zip | bsdtar -C src/entityfish/models/ -xvf-
wget -qO- https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-en.zip | bsdtar -C src/entityfish/models/ -xvf-
```

Run the following command to start the Docker container.
```sh
docker-compose up
```

## Citations
If you find this code useful, please consider citing our work.
```bibtex
@misc{rakotoson2024science,
      title={Science Checker Reloaded: A Bidirectional Paradigm for Transparency and Logical Reasoning}, 
      author={Loïc Rakotoson and Sylvain Massip and Fréjus A. A. Laleye},
      year={2024},
      eprint={2402.13897},
      archivePrefix={arXiv},
      primaryClass={cs.IR}
}
```
If you use the Extractive-Boolean QA For Scientific Fact Checking code implementation, please consider citing the following work.
```bibtex
@inproceedings{Rakotoson_2022,
    series={ICMR ’22},
    title={Extractive-Boolean Question Answering for Scientific Fact Checking},
    url={http://dx.doi.org/10.1145/3512732.3533580},
    DOI={10.1145/3512732.3533580},
    booktitle={Proceedings of the 1st International Workshop on Multimedia AI against Disinformation},
    publisher={ACM},
    author={Rakotoson, Loïc and Letaillieur, Charles and Massip, Sylvain and Laleye, Fréjus A. A.},
    year={2022},
    month=jun,
    collection={ICMR ’22}
}
```

