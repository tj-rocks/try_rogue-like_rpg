import math

def hardcore_round(val, is_hp=False):
    """
    プロジェクト全体で統一する「硬派な丸め」ロジック。
    
    - HP(is_hp=True)の場合:
        小数点以下がわずかでもあれば整数に切り上げます。(例: 10.01 -> 11)
    - その他のステータスの場合:
        小数点第二位がわずかでもあれば、小数点第一位に切り上げます。(例: 10.01 -> 10.1)
    
    Pythonの int(val + 0.9) のような簡易な方法ではなく、math.ceil を用いて
    厳密に「わずかな上昇も無駄にしない」処理を行います。
    """
    if is_hp:
        return int(math.ceil(val))
    else:
        # 小数点第二位で切り上げ（例: 10.01 -> 10.1）
        # 10倍して切り上げてから1/10に戻す
        return math.ceil(val * 10) / 10.0
