"""
Apache Ant 执行器模块

负责解析build.xml文件，检测可用的构建目标，并执行Ant构建任务。
支持超时控制、输出捕获和错误处理。
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import xml.etree.ElementTree as ET

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import get_config


class AntExecutor:
    """Apache Ant执行器类"""
    
    def __init__(self):
        """初始化Ant执行器"""
        self.config = get_config()
        self.timeout = self.config.get('ant_config.timeout_seconds', 300)
        self.ant_home = self.config.get_ant_home()
        self.java_home = self.config.get_java_home()

    def _creationflags(self) -> int:
        """仅在 Windows 下隐藏控制台窗口。"""
        return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    def _get_java_executable(self) -> Optional[str]:
        return self.config.get_java_command()

    def _get_ant_script(self) -> Optional[str]:
        return self.config.get_ant_command()

    def _get_ant_launcher(self) -> Optional[Path]:
        if not self.ant_home:
            return None
        ant_launcher = Path(self.ant_home) / "lib" / "ant-launcher.jar"
        if ant_launcher.exists():
            return ant_launcher
        return None

    def _build_ant_command(self, build_file: str, target: str = "") -> List[str]:
        ant_launcher = self._get_ant_launcher()
        java_exe = self._get_java_executable()

        if ant_launcher and java_exe:
            cmd = [java_exe, "-jar", str(ant_launcher), "-f", build_file]
        else:
            ant_cmd = self._get_ant_script()
            if not ant_cmd:
                raise FileNotFoundError("未找到可用的 Ant 可执行文件")
            cmd = [ant_cmd, "-f", build_file]

        if target:
            cmd.append(target)

        return cmd

    def _build_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        if self.java_home:
            env['JAVA_HOME'] = self.java_home
        if self.ant_home:
            env['ANT_HOME'] = self.ant_home

        # 清理可能导致 Windows 中文路径失效的 JVM 编码强制参数
        for opt_var in ['JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS']:
            if opt_var in env and env[opt_var]:
                tokens = env[opt_var].split()
                filtered = [t for t in tokens if not t.startswith('-Dsun.jnu.encoding=')]
                env[opt_var] = ' '.join(filtered)
                if not env[opt_var].strip():
                    env.pop(opt_var, None)
        return env
        
    def validate_environment(self) -> Tuple[bool, str]:
        """
        验证Ant执行环境
        
        Returns:
            Tuple[bool, str]: (是否有效, 消息)
        """
        # 检查Java环境
        java_exe = self._get_java_executable()
        if not java_exe:
            return False, "未找到 Java 可执行文件，请设置 JAVA_HOME 或把 java 加入 PATH"
        
        # 检查Ant环境
        ant_launcher = self._get_ant_launcher()
        ant_cmd = self._get_ant_script()
        if not ant_launcher and not ant_cmd:
            return False, "未找到 Ant 可执行文件，请设置 ANT_HOME 或把 ant 加入 PATH"
        
        return True, "Ant环境验证通过"
    
    def parse_build_file(self, build_file: str) -> Dict[str, List[str]]:
        """
        解析build.xml文件，提取可用的构建目标
        
        Args:
            build_file: build.xml文件路径
            
        Returns:
            Dict[str, List[str]]: 包含targets和descriptions的字典
        """
        result = {
            'targets': [],
            'descriptions': [],
            'default_target': '',
            'project_name': '',
            'error': None
        }
        
        try:
            if not os.path.exists(build_file):
                result['error'] = f"构建文件不存在: {build_file}"
                return result
            
            # 解析XML文件
            tree = ET.parse(build_file)
            root = tree.getroot()
            
            # 获取项目信息
            result['project_name'] = root.get('name', 'Unknown Project')
            result['default_target'] = root.get('default', '')
            
            # 提取所有target
            targets = root.findall('.//target')
            for target in targets:
                target_name = target.get('name')
                target_desc = target.get('description', '')
                
                if target_name:
                    result['targets'].append(target_name)
                    result['descriptions'].append(target_desc or f"Target: {target_name}")
            
            print(f"✅ 解析build.xml成功: 项目={result['project_name']}, 目标数={len(result['targets'])}")
            
        except ET.ParseError as e:
            result['error'] = f"XML解析错误: {e}"
            print(f"❌ XML解析失败: {e}")
        except Exception as e:
            result['error'] = f"解析build.xml时发生错误: {e}"
            print(f"❌ 解析build.xml失败: {e}")
        
        return result
    
    def execute_ant_command(self, build_file: str, target: str = "") -> Tuple[bool, str, str]:
        """
        执行Ant构建命令
        
        Args:
            build_file: build.xml文件路径
            target: 构建目标，为空则使用默认目标
            
        Returns:
            Tuple[bool, str, str]: (是否成功, 标准输出, 错误输出)
        """
        # 验证环境
        valid, msg = self.validate_environment()
        if not valid:
            return False, "", msg
        
        try:
            cmd = self._build_ant_command(build_file, target)
            env = self._build_env()
            
            print(f"🚀 执行Ant命令: {' '.join(cmd)}")
            print(f"📂 工作目录: {Path(build_file).parent}")
            
            # 执行命令（隐藏控制台窗口）
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                cwd=Path(build_file).parent,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # 使用字节模式
                creationflags=self._creationflags()
            )
            
            # 等待命令完成或超时
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=self.timeout)
                execution_time = time.time() - start_time
                
                # 智能解码输出
                def smart_decode(byte_data):
                    if not byte_data:
                        return ""
                    for encoding in ['utf-8', 'gbk', 'cp936', 'latin1']:
                        try:
                            return byte_data.decode(encoding)
                        except UnicodeDecodeError:
                            continue
                    return byte_data.decode('utf-8', errors='replace')
                
                stdout = smart_decode(stdout_bytes)
                stderr = smart_decode(stderr_bytes)
                
                if process.returncode == 0:
                    print(f"✅ Ant构建成功 (耗时: {execution_time:.2f}秒)")
                    return True, stdout, stderr
                else:
                    print(f"❌ Ant构建失败 (返回码: {process.returncode})")
                    return False, stdout, stderr
                    
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"⏰ Ant构建超时 (超过{self.timeout}秒)")
                return False, "", f"构建超时，已终止进程 (超过{self.timeout}秒)"
            
        except Exception as e:
            error_msg = f"执行Ant命令时发生错误: {e}"
            print(f"❌ {error_msg}")
            return False, "", error_msg
    
    def execute_ant_command_realtime(self, build_file: str, target: str = "", 
                                     output_callback=None, process_callback=None) -> Tuple[bool, float]:
        """
        执行Ant构建命令（支持实时输出）
        
        Args:
            build_file: build.xml文件路径
            target: 构建目标，为空则使用默认目标
            output_callback: 输出回调函数，接收(line, is_error)参数
            process_callback: 进程回调函数，接收process对象，用于取消操作
            
        Returns:
            Tuple[bool, float]: (是否成功, 执行时间)
        """
        # 验证环境
        valid, msg = self.validate_environment()
        if not valid:
            if output_callback:
                output_callback(f"环境验证失败: {msg}\n", True)
            return False, 0.0
        
        try:
            cmd = self._build_ant_command(build_file, target)
            env = self._build_env()
            
            if output_callback:
                output_callback(f"🚀 执行Ant命令: {' '.join(cmd)}\n", False)
                output_callback(f"📂 工作目录: {Path(build_file).parent}\n", False)
            
            # 执行命令（隐藏控制台窗口）
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                cwd=Path(build_file).parent,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # 使用字节模式，稍后手动处理编码
                creationflags=self._creationflags()
            )
            
            # 将进程对象传递给回调
            if process_callback:
                process_callback(process)
            
            # 创建线程来读取标准输出和错误输出
            stdout_lines = []
            stderr_lines = []
            
            def decode_bytes(byte_data):
                """智能解码字节数据"""
                if not byte_data:
                    return ""
                
                # 尝试多种编码格式
                encodings = ['utf-8', 'gbk', 'cp936', 'latin1', 'ascii']
                
                for encoding in encodings:
                    try:
                        return byte_data.decode(encoding)
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                
                # 如果所有编码都失败，使用错误处理
                try:
                    return byte_data.decode('utf-8', errors='replace')
                except:
                    return byte_data.decode('latin1', errors='replace')
            
            def read_stdout():
                """读取标准输出"""
                try:
                    for line_bytes in iter(process.stdout.readline, b''):
                        if line_bytes:
                            line = decode_bytes(line_bytes)
                            stdout_lines.append(line)
                            if output_callback:
                                output_callback(line, False)
                    process.stdout.close()
                except Exception as e:
                    if output_callback:
                        output_callback(f"读取输出时发生错误: {e}\n", True)
            
            def read_stderr():
                """读取错误输出"""
                try:
                    for line_bytes in iter(process.stderr.readline, b''):
                        if line_bytes:
                            line = decode_bytes(line_bytes)
                            stderr_lines.append(line)
                            if output_callback:
                                output_callback(line, True)
                    process.stderr.close()
                except Exception as e:
                    if output_callback:
                        output_callback(f"读取错误输出时发生错误: {e}\n", True)
            
            # 启动读取线程
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待进程完成或超时
            try:
                process.wait(timeout=self.timeout)
                execution_time = time.time() - start_time
                
                # 等待读取线程完成
                stdout_thread.join(timeout=5)
                stderr_thread.join(timeout=5)
                
                success = process.returncode == 0
                
                if output_callback:
                    if success:
                        output_callback(f"\n✅ Ant构建成功 (耗时: {execution_time:.2f}秒)\n", False)
                    else:
                        output_callback(f"\n❌ Ant构建失败 (返回码: {process.returncode})\n", True)
                
                print(f"{'✅' if success else '❌'} Ant构建{'成功' if success else '失败'} (耗时: {execution_time:.2f}秒)")
                return success, execution_time
                    
            except subprocess.TimeoutExpired:
                process.kill()
                execution_time = time.time() - start_time
                if output_callback:
                    output_callback(f"\n⏰ Ant构建超时 (超过{self.timeout}秒)\n", True)
                print(f"⏰ Ant构建超时 (超过{self.timeout}秒)")
                return False, execution_time
            
        except Exception as e:
            error_msg = f"执行Ant命令时发生错误: {e}"
            if output_callback:
                output_callback(f"❌ {error_msg}\n", True)
            print(f"❌ {error_msg}")
            return False, 0.0
    
    def get_ant_version(self) -> Optional[str]:
        """
        获取Ant版本信息
        
        Returns:
            Optional[str]: Ant版本字符串，获取失败返回None
        """
        try:
            ant_cmd = self._get_ant_script()
            if not ant_cmd:
                return None

            env = self._build_env()
            
            process = subprocess.Popen(
                [ant_cmd, "-version"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # 使用字节模式
                creationflags=self._creationflags()
            )
            
            stdout_bytes, stderr_bytes = process.communicate(timeout=10)
            
            if process.returncode == 0 and stdout_bytes:
                # 智能解码输出
                try:
                    # 尝试多种编码
                    for encoding in ['utf-8', 'gbk', 'cp936', 'latin1']:
                        try:
                            stdout = stdout_bytes.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        # 如果所有编码都失败，使用错误处理
                        stdout = stdout_bytes.decode('utf-8', errors='replace')
                    
                    # 提取版本信息
                    for line in stdout.split('\n'):
                        if 'Apache Ant' in line:
                            return line.strip()
                except Exception:
                    return None
            
            return None
            
        except Exception as e:
            print(f"❌ 获取Ant版本失败: {e}")
            return None
    
    def list_common_targets(self) -> List[str]:
        """
        获取常用的构建目标列表
        
        Returns:
            List[str]: 常用目标列表
        """
        return self.config.get('ant_config.common_targets', [
            'compile', 'build', 'clean', 'test', 'package', 'deploy'
        ])
    
    def create_build_log(self, build_file: str, target: str, success: bool, 
                        stdout: str, stderr: str, execution_time: float) -> str:
        """
        创建构建日志
        
        Args:
            build_file: 构建文件路径
            target: 构建目标
            success: 是否成功
            stdout: 标准输出
            stderr: 错误输出
            execution_time: 执行时间
            
        Returns:
            str: 日志文件路径
        """
        try:
            log_dir = Path(build_file).parent / "ant-build-logs"
            log_dir.mkdir(exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"ant_build_{timestamp}.log"
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"Ant Build Log - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n")
                f.write(f"构建文件: {build_file}\n")
                f.write(f"构建目标: {target or '默认目标'}\n")
                f.write(f"执行结果: {'成功' if success else '失败'}\n")
                f.write(f"执行时间: {execution_time:.2f}秒\n")
                f.write(f"Ant版本: {self.get_ant_version() or '未知'}\n")
                f.write("\n" + "=" * 60 + "\n")
                f.write("标准输出:\n")
                f.write("-" * 60 + "\n")
                f.write(stdout)
                f.write("\n\n" + "=" * 60 + "\n")
                f.write("错误输出:\n")
                f.write("-" * 60 + "\n")
                f.write(stderr)
                f.write("\n")
            
            print(f"📄 构建日志已保存: {log_file}")
            return str(log_file)
            
        except Exception as e:
            print(f"❌ 创建构建日志失败: {e}")
            return ""


if __name__ == "__main__":
    # 测试Ant执行器
    executor = AntExecutor()
    print("📋 Ant执行器测试:")
    print(f"环境验证: {executor.validate_environment()}")
    print(f"Ant版本: {executor.get_ant_version()}")
    print(f"常用目标: {executor.list_common_targets()}") 
