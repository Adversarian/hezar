import os
from dataclasses import dataclass
from typing import List

from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer as HFTokenizer
from tokenizers import models, decoders, trainers

from .tokenizer import Tokenizer, TokenizerConfig, TokenizerTrainConfig
from ...constants import DEFAULT_TOKENIZER_FILE, DEFAULT_TOKENIZER_CONFIG_FILE
from ...registry import register_preprocessor
from ...utils.hub_utils import resolve_pretrained_path


@dataclass
class WordPieceTrainConfig(TokenizerTrainConfig):
    name: str = "wordpiece_tokenizer"
    vocab_size: int = 30000
    min_frequency: int = 2
    limit_alphabet: int = 1000
    initial_alphabet = []
    show_progress: bool = True


@dataclass
class WordPieceConfig(TokenizerConfig):
    name: str = "wordpiece_tokenizer"
    max_length: int = 512
    truncation_strategy: str = "longest_first"
    truncation_direction: str = "right"
    stride: int = 0
    padding_strategy: str = "longest"
    padding_direction: str = "right"
    pad_to_multiple_of: int = 0
    pad_token_id: int = 0
    pad_token: str = "[PAD]"
    pad_token_type_id: int = 0
    special_tokens = ["[UNK]", "[SEP]", "[CLS]", "[PAD]", "[MASK]"]
    unk_token: str = "[UNK]"
    wordpieces_prefix: str = "##"
    train_config: WordPieceTrainConfig = WordPieceTrainConfig()


@register_preprocessor("wordpiece_tokenizer", config_class=WordPieceConfig)
class WordPieceTokenizer(Tokenizer):
    """
    A standard WordPiece tokenizer using 🤗HuggingFace Tokenizers

    Args:
        config: Preprocessor config for the tokenizer
        kwargs: Extra/manual config parameters
    """

    tokenizer_filename = DEFAULT_TOKENIZER_FILE
    tokenizer_config_filename = DEFAULT_TOKENIZER_CONFIG_FILE
    token_ids_name = "token_ids"

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)

    def build(self):
        pretrained_path = self.config.pop("pretrained_path")
        if pretrained_path:
            if not os.path.isdir(pretrained_path):
                path = resolve_pretrained_path(pretrained_path)
                tokenizer_path = hf_hub_download(
                    path,
                    filename=self.tokenizer_filename,
                    subfolder=self.preprocessor_subfolder,
                )

            else:
                tokenizer_path = os.path.join(
                    pretrained_path,
                    self.preprocessor_subfolder,
                    self.tokenizer_filename,
                )
            tokenizer = HFTokenizer.from_file(tokenizer_path)
        else:
            tokenizer = HFTokenizer(models.WordPiece(unk_token=self.config.unk_token))  # noqa
            tokenizer.add_special_tokens(self.config.special_tokens)
            tokenizer.decoder = decoders.WordPiece(self.config.wordpieces_prefix)  # noqa

        return tokenizer

    def train(self, files: List[str], config: WordPieceTrainConfig):
        """Train the model using the given files"""

        trainer = trainers.WordPieceTrainer(
            vocab_size=config.vocab_size,
            min_frequency=config.min_frequency,
            limit_alphabet=config.limit_alphabet,
            initial_alphabet=config.initial_alphabet,
            special_tokens=self.config.special_tokens,
            show_progress=config.show_progress,
            continuing_subword_prefix=self.config.wordpieces_prefix,
        )
        if isinstance(files, str):
            files = [files]
        self._tokenizer.train(files, trainer=trainer)

    def train_from_iterator(self, dataset: List[str], config: WordPieceTrainConfig):
        """Train the model using the given files"""

        trainer = trainers.WordPieceTrainer(
            vocab_size=config.vocab_size,
            min_frequency=config.min_frequency,
            limit_alphabet=config.limit_alphabet,
            initial_alphabet=config.initial_alphabet,
            special_tokens=self.config.special_tokens,
            show_progress=config.show_progress,
            continuing_subword_prefix=self.config.wordpieces_prefix,
        )
        self._tokenizer.train_from_iterator(dataset, trainer=trainer, length=len(dataset))