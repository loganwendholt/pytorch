import torch
from torch.fx import Node
from typing import (
    Callable,
)
from torch.ao.quantization._pt2e.quantizer import (
    QuantizationAnnotation,
    SharedQuantizationSpec,
)

def _is_share_obs_or_fq_op(op: Callable) -> bool:
    return op in [
        torch.ops.aten.hardtanh.default,
        torch.ops.aten.mean.default,
        torch.ops.aten.mean.dim,
        torch.ops.aten.adaptive_avg_pool2d.default,
        torch.ops.aten.view_copy.default,
        torch.ops.aten.view.default,
    ]

def propagate_annotation(model: torch.fx.GraphModule) -> None:
    for n in model.graph.nodes:
        if n.op != "call_function" or not _is_share_obs_or_fq_op(n.target):
            continue

        prev_node = n.args[0]
        if not isinstance(prev_node, Node):
            continue

        quantization_annotation = prev_node.meta.get("quantization_annotation", None)
        if not quantization_annotation:
            continue

        output_qspec = quantization_annotation.output_qspec
        if not output_qspec:
            continue

        # make sure current node is not annotated
        if "quantization_annotation" in n.meta and n.meta["quantization_annotation"]._annotated:
            continue

        shared_qspec = SharedQuantizationSpec(prev_node)
        # propagate the previous output_qspec to the current node
        n.meta["quantization_annotation"] = QuantizationAnnotation(
            input_qspec_map = {
                "input_act_obs_or_fq_ctr": shared_qspec,
            },
            output_qspec=shared_qspec,
            _annotated=True,
        )
