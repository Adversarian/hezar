"""
A DISTILBERT model for sequence labeling built using HuggingFace Transformers
"""
from typing import Dict, List, Union

from torch import nn
from transformers import DistilBertConfig, DistilBertModel

from ....registry import register_model
from ..sequence_labeling import SequenceLabelingModel
from .distilbert_sequence_labeling_config import DistilBertSequenceLabelingConfig


@register_model("distilbert_sequence_labeling", DistilBertSequenceLabelingConfig)
class DistilBertSequenceLabeling(SequenceLabelingModel):
    tokenizer_name = "wordpiece_tokenizer"

    def __init__(self, config: DistilBertSequenceLabelingConfig, **kwargs):
        super().__init__(config, **kwargs)
        self.distilbert = DistilBertModel(self._build_inner_config())
        classifier_dropout = (
            config.classifier_dropout if config.classifier_dropout is not None else config.hidden_dropout_prob
        )
        self.dropout = nn.Dropout(classifier_dropout)
        self.classifier = nn.Linear(config.dim, config.num_labels)

    def _build_inner_config(self):
        """
        Build the inner config for DistilBert. If `num_labels` is not provided, it will be inferred from `id2label`.
        If only `num_labels` is provided, `id2label` will be inferred from `num_labels` using the default label names.
        :return:
        """
        if self.config.num_labels is None and self.config.id2label is None:
            raise ValueError("Both `num_labels` and `id2label` are None. Please provide at least one of them!")
        if self.config.id2label is not None and self.config.num_labels is None:
            self.config.num_labels = len(self.config.id2label)
        config = DistilBertConfig(**self.config)
        return config

    def forward(self, inputs, **kwargs) -> Dict:
        input_ids = inputs.get("token_ids")
        attention_mask = inputs.get("attention_mask", None)
        head_mask = inputs.get("head_mask", None)
        inputs_embeds = inputs.get("inputs_embeds", None)
        output_attentions = inputs.get("output_attentions", None)
        output_hidden_states = inputs.get("output_hidden_states", None)

        lm_outputs = self.distilbert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
        )
        sequence_output = lm_outputs[0]

        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)

        outputs = {
            "logits": logits,
            "hidden_states": lm_outputs.hidden_states,
            "attentions": lm_outputs.attentions,
            **inputs
        }
        return outputs
