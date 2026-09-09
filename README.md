# humanize-evals

中文改写质量评测：比较去套话后是否保住事实、原意、声音，以及表达是否更自然。当前仓库保持私有；无新100分制实测排名，不将旧试验分数换算成新榜。

## 当前内容

- 10维100分标准，最终均值保留两位小数，严重事实错误单列。
- 94个开发案例：88个外部英文案例、6个合成中文案例。已完整收录，不代表已全部运行。
- Python标准库CLI：数据校验、逐例适配器调用、匿名评审包、分语言评分汇总。
- 单元与端到端自检；测试适配器只回传原文，不能用其结果证明任何Skill效果。

## 快速开始

需要Python 3.10或更新版本，无第三方依赖。以下命令在仓库根运行。

```bash
python3 evals.py validate
python3 -m unittest discover -s tests -v
# 自检调用链，非模型评测
python3 evals.py run --arm baseline --model smoke-echo --limit 2 --repeats 1 --out runs/smoke/base.jsonl --command python3 tests/echo_adapter.py
python3 evals.py blind --out runs/smoke/blind runs/smoke/base.jsonl
# 人工填写生成的ratings.json中的等级、证据与评审身份后：
python3 evals.py score --ratings runs/smoke/blind/ratings.json --key runs/smoke/blind/key.json
```

正式测评将--command换成你自己的模型适配器，--model记录实际请求模型名，去掉--limit并用--repeats 3。适配器接收JSON stdin，返回{"text":"改稿正文"}；可额外返回usage，禁止输出凭证。基线不加规则，各Skill使用--skill private/某规则快照.md，使用相同模型和生成设置。规则需要引用文件时，先按其许可与加载契约整理为固定快照；本接口测单次上下文规则效果，不代表完整Agent工作流。

将各条件run文件一起传给blind。错误输出不会进入评审，条件不齐会拒绝组包；先检查并单独重跑完整实验，不只挑选成功答案。原文参考用run --original。runs/和private/默认不提交。

## 评分与测试方法

| 维度 | 权重 |
|---|---:|
| 事实准确与完整 | 20 |
| 原意与逻辑 | 15 |
| 连贯性 | 10 |
| 作者声音 | 10 |
| 情绪适配 | 10 |
| 真实感 | 10 |
| 活人感与自然度 | 10 |
| 符号与标点 | 5 |
| 信息清晰与密度 | 5 |
| 修改克制与任务遵循 | 5 |

每维0—4等级附证据，加权后按语言显示100分成绩。详细边界见[评分标准](docs/SCORING.md)，运行约定见[实验流程](docs/PROTOCOL.md)。两位小数只表示显示精度，微小分差不能直接宣布胜负。教学、开发、留出必须分开；当前没有独立留出集。

## 借鉴与开源来源

| 来源 | 实际用途 | 本仓库收录情况 |
|---|---|---|
| [Slopkit](https://github.com/ehmo/slopkit/tree/b33718bb9283c11b09567dc714f92d90ffb7bd16/skills/slopbeth/benchmarks) | 改写输入、事实断言和分类 | 复制88例原始语料并生成适配层；MIT许可保留于data/upstream/slopkit/LICENSE |
| [Humanizer-zh](https://github.com/op7418/Humanizer-zh) | 参赛规则与中文示例参考 | 已收录Markdown规则与示例；版本91f3d394db8419c20d67ebe22a96cf8fee0a404b |
| [stop-slop](https://github.com/hardikpandya/stop-slop) | 短语、结构、节奏与示例参考 | 已收录Markdown规则与示例；版本8da1f030185bdfe8471220585162991eaeb970e9 |
| [Tramstop](https://github.com/alchaincyf/tramstop-skill) | 素材与编辑流程参考 | 已收录Markdown规则与示例；版本2f7808859e260ac9eb79bb3836bce1cd3eb2ba2e |
| [Humanizer](https://github.com/blader/humanizer) | 参赛规则与事实保留机制参考 | 已收录Markdown规则与示例；版本9862685f575c65a8247f90369951df1b3416e3d6 |
| [kimhons/humanize](https://github.com/kimhons/humanize) | 英文文风规则扫描参考 | 已收录Markdown参考与许可，不作为评分依赖，不直接用于中文排名 |
| [C-ReD](https://github.com/HeraldofLight/C-ReD) | 中文人类/机器来源检测语料参考 | 未下载；来源识别不等于编辑质量 |
| [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt) | 机器文本来源检测方法参考 | 未部署、未复制；不作为唯一质量判据 |

初版仅复制Slopkit；本轮进一步复制公开规则与教学示例，最新明细以[data/sources.json](data/sources.json)为准，不暗示其作者认可本仓库。后续复制第三方文件必须逐项核对许可、保留署名与版本。Skill教学例已被规则使用，不能标为未见测试。自有参赛规则由本地private/加载，不上传内部快照。

## 数据边界与局限

原始公开语料SHA256及版本见[data来源记录](data/upstream/slopkit/source.json)。全部案例范围见[data说明](data/README.md)。原始参考答案不是唯一正确答案，供应方字面断言会误报同义改写；禁止拿字串通过率冒充语义准确率。私人会话、真实作者草稿和原始调用日志不在仓库中。

首版不提供训练、在线服务、模型账号配置或检测器概率，不自动修改参赛Skill、不发布文章。尚未运行新的模型PK，也未实现置信区间、跨模型实验和长文专项榜。

## 多账号Git环境

若全局URL重写影响认证，可对当前命令设置`GIT_CONFIG_GLOBAL=/dev/null`并从环境显式提供目标账号凭证，使用仓库级凭证助手。不要把Token写进remote URL、命令参数或仓库文件；不要打印完整Git配置用于诊断。

## 来源清点

8个仓库的版本、可用数据路径、许可判断和51个实际复制文件见[data/sources.json](data/sources.json)。data/reference/保留上游原始字节与许可证；案例、供应方输出、评分历史不能混算数量。C-ReD缺少明确许可，Fast-DetectGPT第三方数据许可尚未逐项核对，二者仅登记路径未复制正文。
