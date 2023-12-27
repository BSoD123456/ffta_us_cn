# FFTA 美版汉化工具集

## 概述

本脚本工具集用于将GBA游戏FFTA的日版汉化版文本，移往美版ROM，并提供进一步汉化美版新内容的工具。

## 功能

- 导出原日版汉化/美版英文对照文本
- 导出英文独占内容文本
- 将原日版汉化文本导入美版ROM
- 将新英文文本导入美版ROM
- 将汉化版字库导入美版ROM

不包括的功能

- 不对ROM图片内容进行任何修改，包括各种图标以及美术字体文本。
- 一些零散的UI文本，不在导出文本中，也暂时不会被汉化。（其实大部分没有导出的UI文本都是图片。）
- 新的美版独占英文文本并没有完成汉化。

## 用法

### 环境

- 克隆本项目。
- 找到FFTA熊组yggdra修正小字版汉化ROM，FFTA美版ROM。
- 如果你需要用更多分析功能，则还需要找到FFTA日版ROM。
- 在工程根目录下新建roms文件夹，将上述ROM文件放到工程roms目录下，并分别改名为fftaus.gba（美版），fftacnb.gba（汉化原版），fftajp.gba（日版）。
- 或者修改ffta_modifier.py脚本中CONF配置里的文件名到对应ROM文件。

### 打包美版汉化ROM

运行ffta_modifier.py脚本，没有报错的完整运行后（且没有警告），就会在工程roms目录下出现fftauscn.gba文件，就是美版汉化ROM。

## 进一步汉化新文本

如果你愿意对英文独占文本进行进一步汉化的话，请阅读以下部分。

### 汉化文件

- raw_txt_comp_wk.json为英汉对照文本，仅供对照。
- raw_txt_uncv_wk.json为英语独占文本，仅供对照。
- trans_txt.json为英语独占文本汉化文件，用于汉化。
- trans_fix_txt.json为原汉化文本修正文件，用于汉化。

汉化文件中的文本符号遵循以下规则：

- #号后的内容都不进行导入，由#开头的句子仅供参考，甚至可能不具备参考意义。
- @号后接[]的内容为控制符，必须严格按照原本形式保留。
- 文本中所有标点，除了句号（。）引号和省略号以外，其他全部是英文半角标点（尤其注意**逗号感叹号问号是半角**）。
- 在条目索引号前带有#号的条目，为美版中并没有或者并不需要的条目，无需翻译，也不会出现在独占文本文件中。

### 修改汉化文本

- 仅需修改trans_txt.json文件即可。
- 该文件内的翻译条目内，已经预先填写了**未经检查**过的**机翻**内容。但是这些文本都由#号开头并不会被导入到ROM中。
- 预置的**机翻**文本仅供翻译时的参考，**绝对不应该**不经润色直接用于汉化。
- 并非#号开头的句子，是**已经完成汉化润色并已导入游戏**的句子，**不需要**重复翻译。
- 对句子的翻译直接在#号开头的文本中修改或覆盖，完成修改后，去掉行头的#，即可被视为有效汉化文本。
- 常见控制符：
    - @[4D] 为换行符。汉化时应自己根据文本长短调整换行符的位置和数量。（一行大概14个汉字是极限长度，但是一般最好保持在10个汉字以下。通常第一行最短，下面的行更长，视觉效果更好。）
    - @[4F]@[42] 为分页符。汉化时应依语句段落完整保留所有分页符。
    - @[40]@[42] 为文本段尾符。汉化时应完整保留所有段尾符。
    - @[51xx] 为引用文本。xx为16进制的文本引用索引号，对应在words:refer表中的文本。比如@[5117]就是words:refer中的第0x17=23号文本"Judge" "裁判"。
    - @[ ] 为特殊终结符。汉化时直接保留，但是注意方括号间有**1个空格**。
    - 数字较大的一般为变量替换符，应视为某个单词，严格保留在原句位置。
    - 其他控制符也应该根据上下文选择合适进行保留。
- 英文原文为多句点的省略号，尽量在翻译中使用中文全角省略号（……）来替换。使用6点省略号（……）还是3点省略号（…）可视上下文决定。
- 修改完成后运行ffta_modifier.py脚本如果出现了未知字符相关的warning，表示文本中使用了并不支持的汉字或者符号。请自行替换成其他符号。如果实在有无法替代的汉字，请在项目issue中提出。

### 修正原汉化文本

- 原汉化文本并不在上述汉化文件中，而是在raw_txt_comp_wk.json中。若需要修改原汉化文本，**请勿直接修改**raw_txt_comp_wk.json文件，该文件由脚本自动生成并维护，不应手动修改。
- 若需要修改原汉化文本，需要首先在trans_fix_txt.json文件中创建所要修改的索引号的条目。条目的内容可以为任意非文本对（双文本数组），一般使用null即可。
- 例如现在我想要修改条目：fx_text中的21/325和25/99，以及words:content中的598，就可以在trans_fix_txt.json中写入如下内容：

> `{"fx_text":{"21/325":null, "25/99":null}, "words:content":{"598": null}}`

- 接下来运行ffta_modifier.py脚本，脚本会自动将上述条目的原文和翻译对照内容填写进trans_fix_txt.json文件中。
- 然后再次打开trans_fix_txt.json文件，找到想要修改的条目，和上述修改汉化文本一样，修改翻译内容即可。
- 修改完成后最后再运行一次ffta_modifier.py脚本，即可导入修正内容。

### 提交修改后的汉化内容

- 可以直接在本项目中发起Pull-Request。
- 或者不想折腾，就直接在项目issue中以任何方式分享你修改完成的trans_txt.json文件。
- 但是注意，在决定翻译以前，请先通过事先发起一个空Pull-Request，或者发布issue的方式，选择将要汉化的范围（索引号范围）占个坑，以免重复劳动。
- 所有占坑时效为48小时，超过时间即认为放弃占坑。请酌情选择能短时间内完成的内容占坑。

### 另外的

由于我并不打算对游戏内图片进行修改，也并不想加入额外文本。因此游戏内并不会留下汉化人员名单。

如果你有帮助进行汉化，在我发布的后续版本中，我只会在一份独立于ROM文件以外的额外名单里记下你的ID。

## 授权

如果你愿意，你可以自行FORK本项目后，自行发布你的汉化版本。

但是请在发布版本中保留你FORK时版本的本项目中的credits.txt名单文件。

在同意上述要求的前提下，本项目代码由GPLv3协议授权。

游戏所有原版内容相关权利全部属于游戏原厂商。

原版汉化内容相关权利属于原汉化组。

脚本中使用的字体相关权利属于原作者。

本项目并不对任何用户的使用后果负责任。
