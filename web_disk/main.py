import os
import socket
import sys
from flask import Flask, render_template, url_for, redirect, send_from_directory, request
from urllib.parse import unquote, quote

app = Flask(__name__)

# 根目录设置
rootdir = sys.argv[1]

# 端口
port = sys.argv[2]

# 显示特定开头的文件
sysfile_display = "Y"  # 可选参数"Y" or "N"
undisplay_list = [".", "_", "__"]  # 隐藏文件开头格式，如上一个参数为“Y”则无效


@app.route('/')
@app.route('/<subdir>/')
def document(subdir=''):
    if rebuild_url():
        # 不显示文件列表第一个返回目录："../"
        undisplay_first = 0
        # 名字小于工作目录，切换到根目录
        # print(f"切换到目录：{rootdir}")
        os.chdir(rootdir)
    else:
        full_path = unquote(request.full_path).replace("+", " ")
        if os.path.isfile(full_path[6:]):
            # 由于百分码的保留机制：编码dir 成为 url：即将dir中的“/”变为“%2F”，该规则遵循百分码编码
            downloader_dir = full_path[7:].replace("/", "%2F")
            return redirect(url_for("downloader", full_name=downloader_dir))
        else:
            undisplay_first = 1
            # 切到其他目录
            # print(f"切换到目录：{request.full_path[6:]}")
            # 百分码转为utf-8
            # 将"+"转为" "
            os.chdir(full_path[6:])

    current_dir = os.getcwd() + "/"
    # print(f"当前目录：{current_dir}")
    current_list = os.listdir(current_dir)
    # print(f"当前目录下文件：{current_list}")
    current_list = sorted_dir(current_list)
    contents = []
    for i in current_list:
        sys_path_file = os.getcwd() + os.sep + i
        if os.path.isdir(sys_path_file):
            extra = os.sep
        else:
            extra = ''
        content = {}
        content['filename'] = i + extra
        contents.append(content)
    return render_template('main.html', contents=contents, subdir=current_dir, ossep=os.sep,
                           pre_dir=get_predir(current_dir), rootdir=rootdir, undisplay_first=undisplay_first)


# 下载命令
@app.route('/download/<full_name>', methods=['GET'])
def downloader(full_name):
    filename = full_name.split("%2F")[-1]
    return send_from_directory(os.getcwd(), filename, as_attachment=True)


# 上传命令
@app.route("/upload", methods=["POST"])
@app.route('/<updir>/')
def upload_file():
    upload_dir = os.getcwd()
    back_url_base = "http://" + get_host_ip() + ":" + str(port) + "/?dir="
    back_url = back_url_base + quote(upload_dir)
    try:
        for f in request.files.getlist('file'):
            file_fullname = os.path.join(upload_dir, f.filename)
            upload_filename = f.filename
            f.save(file_fullname)
        return render_template('upload.html', result="文件上传成功！", back_url=back_url, filename=upload_filename,
                               file_dir=file_fullname, file_size=get_size(file_fullname))
    except Exception as e:
        return render_template('upload.html', result="文件上传失败！")


# 获取前一个url
def get_predir(current_dir):
    """
        返回上级目录
        :return: ip
    """
    sub_url = "http://" + get_host_ip() + ":" + str(port)
    pre_sys_path_list = current_dir.split('/')
    pre_sys_pop_list = pre_sys_path_list[:len(pre_sys_path_list) - 2]
    pre_dir_connect = "/".join(pre_sys_pop_list)
    pre_dir = sub_url + "/?dir=" + pre_dir_connect + "/"
    return pre_dir


# 获取运行程序主机ip地址
def get_host_ip():
    """
    查询本机ip地址
    :return: ip
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


# 重定向url
def rebuild_url():
    """
        当访问的url低于工作目录时返回布尔值:True
        :return: bool
    """
    # 获取真实的rootdir目录
    list_dir = []
    list_root_dir = []
    cur_dir_list = request.full_path[6:].split("/")
    for i in cur_dir_list:
        if i:
            list_dir.append(i)
    cur_dir_list = list_dir

    # 获取真实的rootdir目录
    rootdir_list = rootdir.split("/")
    for i in rootdir_list:
        if i:
            list_root_dir.append(i)
    rootdir_list = list_root_dir

    # 当url目录小于当前rootdir目录时返回True
    if len(cur_dir_list) <= len(rootdir_list):
        return True
    else:
        return False


# 计算文件大小并返回数值
def get_size(dir):
    if os.path.getsize(dir) == 0:
        size_zero = 0
        size_zero = str(size_zero)
        size = str(size_zero) + " Kb"
        return size
    else:
        size_kb = os.path.getsize(dir) / 1024
        if 1024 <= size_kb < 1024 ** 2:
            size_mb = round(size_kb / 1024, 2)
            size_mb = str(size_mb)
            size = size_mb + " Mb"
            return size
        elif 1024 ** 2 <= size_kb < 1024 ** 3:
            size_gb = round(size_kb / 1024 ** 2, 2)
            size_gb = str(size_gb)
            size = size_gb + " Gb"
            return size
        elif 1024 ** 3 <= size_kb < 1024 ** 4:
            size_tb = round(size_kb / 1024 ** 3, 2)
            size_tb = str(size_tb)
            size = size_tb + " Tb"
            return size
        else:
            size_kb = round(size_kb, 2)
            size_kb = str(size_kb)
            size = size_kb + " Kb"
            return size


# web显示列表处理
def sorted_dir(list):
    """
        返回处理完成的文件名列表（排序，去除特定开头的文件）
        :return: all_name
    """
    dirs = []
    files = []
    subdir = os.getcwd()

    # # 去除特定开头的文件
    if not sysfile_display == "Y":
        diff_list = []
        filter_list = []
        for i in list:
            for j in undisplay_list:
                if i[:len(j)] == j:
                    diff_list.append(i)
        for i in diff_list:
            if diff_list.count(i) > 1:
                for j in range(diff_list.count(i) - 1):
                    diff_list.remove(i)
        for i in list:
            if i not in diff_list:
                filter_list.append(i)
        list = filter_list

    # 排序（按照文件在前文件在后）
    for name in range(len(list)):
        file_dir = subdir + "/" + list[name]
        # 如果是目录，添加进入目录列表，否则添加进文件列表
        if os.path.isdir(file_dir):
            dirs.append(list[name])
        else:
            files.append(list[name])
    dirs.sort()
    files.sort()
    all_name = dirs + files
    return all_name


if __name__ == '__main__':
    app.run(host=get_host_ip(), port=port, debug=True)
