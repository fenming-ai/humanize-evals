# 案例合同与校准

pilot-v1.json记录首批100条候选。annotations/为初标输出，reviews/为独立上下文模型复核，reviews-initial/保留早期重复复核的初次记录。prompts/冻结提示与结构；rejections.json保存淘汰理由。initial-candidates.json与reserve-candidates.json记录来源、分组和初始状态，候选不能直接计入正式榜。

均为模型辅助审核，human_reviewed=false。同一请求模型gpt-6-astra、medium，分开上下文；没有人工逐例终审。最终500名单见../curated/zh-v1.jsonl；筛选、标点合同升级与功能等效解释见../../docs/DATA_BUILD.md。
