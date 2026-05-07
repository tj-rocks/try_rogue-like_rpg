import time
import functools

def trace_method(func):
    """個別のメソッドにログ出力を適用するデコレータ"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        class_name = ""
        if args and hasattr(args[0], '__class__'):
            class_name = args[0].__class__.__name__
        
        func_name = func.__name__
        timestamp = time.strftime("%H:%M:%S")
        
        # 引数のパース（selfは除外）
        display_args = args[1:] if class_name else args
        args_str = ", ".join([repr(a) for a in display_args] + [f"{k}={repr(v)}" for k, v in kwargs.items()])
        
        print(f"[TRACE] {timestamp} | CALL | {class_name}.{func_name}({args_str})")
        
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        print(f"[TRACE] {timestamp} | RET  | {class_name}.{func_name} -> {repr(result)} ({duration:.4f}s)")
        return result
    return wrapper

def trace_class(cls):
    """クラス内のすべてのメソッド（特定を除く）にログ出力を適用するクラスデコレータ"""
    # 除外するメソッド（頻度が高いもの、特殊なもの）
    EXCLUDE = ["draw", "update", "operate", "update_animation", "__repr__", "__str__"]
    
    for name, method in cls.__dict__.items():
        if callable(method) and name not in EXCLUDE and not name.startswith("__"):
            setattr(cls, name, trace_method(method))
    return cls
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
 Riverside
