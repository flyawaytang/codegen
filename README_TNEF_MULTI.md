# TNEF多文件嵌入工具

这个项目提供了多种方法来生成包含多个自定义命名文件的TNEF格式文件。

## 方法1：多个TNEF文件

使用`tnef_multi_wrapper.py`脚本创建多个TNEF文件，每个文件包含一个自定义命名的嵌入文件。

### 使用方法

```bash
python tnef_multi_wrapper.py -a "文件1.txt:自定义名称1.txt" -a "文件2.txt:自定义名称2.txt"
```

这将在`tnef_files`目录中创建多个TNEF文件，每个文件包含一个嵌入文件。

### 提取文件

```bash
for f in tnef_files/*.dat; do tnef --number-backups $f; done
```

这将提取所有TNEF文件中的嵌入文件，并使用自定义名称保存。

## 方法2：ZIP归档

使用`tnef_creator_zip.py`脚本创建一个包含ZIP归档的TNEF文件，该ZIP归档包含多个自定义命名的文件。

### 使用方法

```bash
python tnef_creator_zip.py -a "文件1.txt:自定义名称1.txt" -a "文件2.txt:自定义名称2.txt" -z "我的文件.zip"
```

这将创建一个TNEF文件，其中包含一个名为"我的文件.zip"的ZIP归档，该归档包含两个自定义命名的文件。

### 提取文件

```bash
tnef winmail.dat
unzip 我的文件.zip
```

这将首先提取TNEF文件中的ZIP归档，然后从ZIP归档中提取自定义命名的文件。

## 命令行参数

所有脚本都支持以下命令行参数：

- `-a, --attach "文件:名称"` - 指定要嵌入的文件和自定义名称（可多次使用）
- `-f, --file 文件` - 指定要嵌入的文件（可多次使用）
- `-n, --name 名称` - 指定嵌入文件的自定义名称（必须与`--file`选项数量匹配）
- `-j, --json 配置文件` - 指定包含附件规范的JSON配置文件
- `-o, --output 输出文件` - 指定输出的TNEF文件名（默认为winmail.dat）

### JSON配置文件格式

```json
[
  {
    "file": "文件1.txt",
    "name": "自定义名称1.txt"
  },
  {
    "file": "文件2.txt",
    "name": "自定义名称2.txt"
  }
]
```

## 注意事项

- 由于TNEF格式的限制，直接在单个TNEF文件中嵌入多个文件可能会导致与某些TNEF提取工具不兼容。
- 方法1（多个TNEF文件）是最可靠的方法，可以确保与所有TNEF提取工具兼容。
- 方法2（ZIP归档）提供了一种更紧凑的方式来嵌入多个文件，但需要额外的步骤来提取文件。

