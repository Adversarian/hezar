import logging
import os.path
from abc import abstractmethod, ABC
from typing import *
from enum import Enum

from huggingface_hub import HfApi, create_repo
from omegaconf import OmegaConf, DictConfig

from ..configs import ModelConfig
from ..hezar_repo import (HezarRepo,
                          HEZAR_HUB_ID,
                          HEZAR_MODELS_CACHE_DIR,
                          HEZAR_SNAPSHOTS_DIR)
from ..utils import merge_kwargs_into_config
from . import models_registry


class ModelMode(Enum):
    inference = 'inference'
    training = 'training'

    @classmethod
    def list(cls):
        return list(map(lambda c: c.name, cls))


class BaseModel(ABC):
    def __init__(self,
                 config: ModelConfig,
                 mode: ModelMode,
                 repo: HezarRepo = None,
                 **kwargs):
        super(BaseModel, self).__init__()
        self.repo = repo or HezarRepo(config.pretrained_path)
        self.config = merge_kwargs_into_config(config, kwargs)
        self.model = self.build_model(mode=mode)

    def __str__(self):
        return self.model.__str__()

    @classmethod
    def from_pretrained(cls, path, **kwargs):
        repo = HezarRepo(path)
        model_name = repo.get_model_registry_name()
        model_config_class = models_registry[model_name]['model_config']
        config = repo.get_config(model_config_class=model_config_class)
        model = cls(config, mode=ModelMode.inference, repo=repo, **kwargs)
        model_state_dict = repo.get_model(return_state_dict=True)
        model.model.load_state_dict(model_state_dict)
        return model

    def save_pretrained(self, path):
        self.repo.move_repo(self.repo.repo_dir, path, keep_source=True)
        logging.info(f'Model saved to {path}')

    def push_to_hub(self, repo_id):
        api = HfApi()
        models = api.list_models(author=HEZAR_HUB_ID)
        model_names = [model.modelId.split('/')[-1] for model in models]
        if os.path.basename(repo_id) not in model_names:
            create_repo(repo_id)
        else:
            logging.info(f'Repo `{repo_id}` already exists on the Hub, skipping repo creation...')

        # change pretrained_path in config
        config = self.repo.get_config(config_file='config.yaml')
        config.model.pretrained_path = repo_id
        OmegaConf.save(config, f'{self.repo.repo_dir}/config.yaml')

        api.upload_folder(
            folder_path=self.repo.repo_dir,
            repo_id=repo_id,
            repo_type='model',
            path_in_repo='.'
        )
        logging.info(f'Uploaded repo `{repo_id}` to the Hub!')

    @abstractmethod
    def build_model(self, mode: ModelMode):
        raise NotImplementedError

    @abstractmethod
    def forward(self, inputs, **kwargs) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def predict(self, inputs, **kwargs) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def postprocess(self, inputs, **kwargs) -> Dict:
        raise NotImplementedError

