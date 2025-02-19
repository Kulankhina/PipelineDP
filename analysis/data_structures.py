# Copyright 2022 OpenMined.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Contains API dataclasses."""

import copy
import dataclasses
from typing import Callable, Optional, Sequence

import pipeline_dp
from pipeline_dp import input_validators


@dataclasses.dataclass
class PreAggregateExtractors:
    """Data extractors for pre-aggregated data.

    Pre-aggregated data assumptions: each row corresponds to each
    (privacy_id, partition_key) which is present in the original dataset.
    Each row has
      1. count and sum, which correspond to count and sum of values
    contributed by the privacy_id to the partition_key.
      2. n_partitions, which is the number of partitions contributed by
    privacy_id.

    Attributes:
        partition_extractor: a callable, that takes a row of preaggraged data,
          and returns partition key.
        preaggregate_extractor: a callable, that takes a row of preaggraged
        data, and returns (count, sum, n_partitions).
    """
    partition_extractor: Callable
    preaggregate_extractor: Callable


@dataclasses.dataclass
class MultiParameterConfiguration:
    """Specifies parameters for multi-parameter Utility Analysis.

    All MultiParameterConfiguration attributes corresponds to attributes in
    pipeline_dp.AggregateParams.

    UtilityAnalysisEngine can perform utility analysis for multiple sets of
    parameters simultaneously. API for this is the following:
    1. Specify blue-print AggregateParams instance.
    2. Set MultiParameterConfiguration attributes (see the example below). Note
    that each attribute is a sequence of parameter values for which the utility
    analysis will be run. All attributes that have non-None values must have
    the same length.
    3. Pass the created objects to UtilityAnalysisEngine.aggregate().

    Example:
        max_partitions_contributed = [1, 2]
        max_contributions_per_partition = [10, 11]

        Then the utility analysis will be performed for
          AggregateParams(max_partitions_contributed=1, max_contributions_per_partition=10)
          AggregateParams(max_partitions_contributed=2, max_contributions_per_partition=11)
    """
    max_partitions_contributed: Sequence[int] = None
    max_contributions_per_partition: Sequence[int] = None
    min_sum_per_partition: Sequence[float] = None
    max_sum_per_partition: Sequence[float] = None

    def __post_init__(self):
        attributes = dataclasses.asdict(self)
        sizes = [len(value) for value in attributes.values() if value]
        if not sizes:
            raise ValueError("MultiParameterConfiguration must have at least 1"
                             " non-empty attribute.")
        if min(sizes) != max(sizes):
            raise ValueError(
                "All set attributes in MultiParameterConfiguration must have "
                "the same length.")
        if (self.min_sum_per_partition is None) != (self.max_sum_per_partition
                                                    is None):
            raise ValueError(
                "MultiParameterConfiguration: min_sum_per_partition and "
                "max_sum_per_partition must be both set or both None.")
        self._size = sizes[0]

    @property
    def size(self):
        return self._size

    def get_aggregate_params(self, params: pipeline_dp.AggregateParams,
                             index: int) -> pipeline_dp.AggregateParams:
        """Returns AggregateParams with the index-th parameters."""
        params = copy.copy(params)
        if self.max_partitions_contributed:
            params.max_partitions_contributed = self.max_partitions_contributed[
                index]
        if self.max_contributions_per_partition:
            params.max_contributions_per_partition = self.max_contributions_per_partition[
                index]
        if self.min_sum_per_partition:
            params.min_sum_per_partition = self.min_sum_per_partition[index]
        if self.max_sum_per_partition:
            params.max_sum_per_partition = self.max_sum_per_partition[index]
        return params


@dataclasses.dataclass
class UtilityAnalysisOptions:
    """Options for the utility analysis."""
    epsilon: float
    delta: float
    aggregate_params: pipeline_dp.AggregateParams
    multi_param_configuration: Optional[MultiParameterConfiguration] = None
    partitions_sampling_prob: float = 1
    pre_aggregated_data: bool = False

    def __post_init__(self):
        input_validators.validate_epsilon_delta(self.epsilon, self.delta,
                                                "UtilityAnalysisOptions")
        if self.partitions_sampling_prob <= 0 or self.partitions_sampling_prob > 1:
            raise ValueError(
                f"partitions_sampling_prob must be in the interval"
                f" (0, 1], but {self.partitions_sampling_prob} given.")

    @property
    def n_configurations(self):
        if self.multi_param_configuration is None:
            return 1
        return self.multi_param_configuration.size
