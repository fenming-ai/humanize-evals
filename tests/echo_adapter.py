"""仅用于离线验证调用链；不代表模型生成。"""
import json
import sys
print(json.dumps({'text': json.load(sys.stdin)['text']}, ensure_ascii=False))
