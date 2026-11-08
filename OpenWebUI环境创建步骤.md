
conda create --name OpenWebUI python==3.12 -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main

conda activate OpenWebUI

pip isntall open-webui

export HF_HUB_OFFLINE=1

open-webui serve






























