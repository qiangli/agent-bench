# AWS Lambda GPU Inference Costs for Agent Bench

Pricing and platform limits checked on November 23, 2026. All prices are in USD.

For intermittent benchmark runs, start with a pay-as-you-go API that serves the
open-weight model you want to evaluate. Rented GPU capacity can cost less when
batched runs keep it busy enough to beat the API's per-token rate. Hosting the
model yourself also gives you control over the checkpoint and inference runtime.

## Model fit on Lambda

AWS Lambda Managed Instances gives each GPU execution environment one GPU or
GPU fraction. On a multi-GPU host, Lambda creates separate environments instead
of pooling GPU memory. The launch supports selected EC2 G-series families,
including G6e. A `g6e.xlarge` has one NVIDIA L40S with 48 GB of advertised
accelerator memory and 44 GiB listed in the EC2 specifications. The 48 concurrent
invocations in InfoQ's report shared one GPU-resident model. The test used
Gemma 4 E2B. [AWS Lambda GPU limits](https://docs.aws.amazon.com/lambda/latest/dg/lambda-managed-instances-gpu.html) · [EC2 specifications](https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html) · [InfoQ report](https://www.infoq.com/news/2026/11/aws-lambda-gpu-managed-instances/)

| Candidate | Checkpoint size | Implication |
| --- | ---: | --- |
| Qwen3-Next-80B-A3B, 4-bit IQ4_XS | 42.85 GB | A candidate for short contexts and low concurrency, with limited GPU memory left for the runtime and context cache. [Checkpoint](https://huggingface.co/bartowski/Qwen_Qwen3-Next-80B-A3B-Instruct-GGUF) |
| Qwen3.5-122B-A10B, roughly 2-bit UD-IQ2_XXS | 36.6 GB | A plausible fit by weight size, with a more aggressive quality tradeoff. [Checkpoint](https://huggingface.co/unsloth/Qwen3.5-122B-A10B-GGUF/blob/main/Qwen3.5-122B-A10B-UD-IQ2_XXS.gguf) |

These are memory estimates. Both GGUF files exceed Lambda's 32 GB of local
scratch space, so the runtime needs a way to read the checkpoint from external
storage. AWS documents direct S3 streaming for compatible vLLM checkpoints.
The chosen runtime and checkpoint format determine the loading path.
[AWS launch limits](https://aws.amazon.com/blogs/aws/aws-lambda-now-supports-gpu-instances-for-event-functions-on-lambda-managed-instances/) · [AWS inference guide](https://docs.aws.amazon.com/lambda/latest/dg/lambda-managed-instances-gpu-inference.html)

At the other end of the range, Moonshot's 2.8T-parameter Kimi K3.1 Pro has a
documented vLLM deployment on eight NVIDIA B300 GPUs. AWS lists an eight-GPU
EC2 Capacity Block at $129.17 per hour in Oregon and N. Virginia. Modal lists
$56.79 per hour in GPU charges for eight B300s. Moonshot's API lists $2 per
million uncached input tokens and $10 per million output tokens.
[Moonshot model card](https://huggingface.co/moonshotai/Kimi-K3.1-Pro) · [vLLM recipe](https://recipes.vllm.ai/moonshotai/Kimi-K3.1-Pro?hardware=b300&preset=b300_agentx_ep&strategy=single_node_tep) · [AWS Capacity Blocks](https://aws.amazon.com/ec2/capacityblocks/pricing/) · [Modal pricing](https://modal.com/pricing) · [Moonshot API pricing](https://platform.kimi.ai/)

## Billing and break-even for Qwen3-Next-80B-A3B

One Linux `g6e.xlarge` in N. Virginia costs $1.861 per hour on demand. Adding
Lambda's 9.75% GPU management fee gives about **$2.04 per provisioned hour**,
or **3.4 cents per minute**. EC2 bills Linux instance time by the second with a
60-second minimum per launch. Lambda also charges $0.20 per million requests.
Model loading and warm idle time count toward instance time. With scale-to-zero
enabled, charges continue until the instance terminates, which AWS says
typically takes a few minutes. [Regional EC2 rate](https://instances.usage.ai/aws/ec2/region/us-east-1) · [EC2 On-Demand billing](https://aws.amazon.com/ec2/pricing/on-demand/) · [Lambda pricing](https://aws.amazon.com/lambda/pricing/) · [Lambda scaling](https://docs.aws.amazon.com/lambda/latest/dg/lambda-managed-instances-scaling.html)

| Option | Standard rate | Example cost |
| --- | --- | ---: |
| DeepInfra API | $0.09 per million input tokens and $1.10 per million output tokens | $31 for 100M input and 20M output. [Pricing](https://deepinfra.com/Qwen/Qwen3-Next-80B-A3B-Instruct) |
| Amazon Bedrock API, US East | $0.15 per million input tokens and $1.20 per million output tokens | $39 for the same token volume. [Pricing](https://aws.amazon.com/bedrock/pricing/) |
| Lambda GPU | $2.04 per provisioned hour for one instance | $204 for 100 provisioned hours or $1,491 for a 730-hour month, before requests and storage. |

At five input tokens per output token, one million output tokens and the
associated input cost $1.55 on DeepInfra and $1.95 on Bedrock. Using the
unrounded Lambda rate, divide the hourly compute cost by that API cost, then
multiply by one million and divide by 3,600. Lambda breaks even at about
**366 output tokens per billed second** against DeepInfra and **291** against
Bedrock. The throughput is aggregate across all requests and includes idle
and startup time in the denominator. Storage, operations, and discounted API
rates can raise the threshold.

For an agent-bench comparison, record the exact model revision, precision,
context lengths, batching, token totals, and billed instance time alongside
quality and latency scores. DeepInfra lists FP8 for its endpoint. The estimated
Lambda fit uses a 4-bit GGUF checkpoint, so benchmark scores and usable context
can differ even when both deployments use the same base model.
[DeepInfra model details](https://deepinfra.com/Qwen/Qwen3-Next-80B-A3B-Instruct)
