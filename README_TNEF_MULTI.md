# TNEF多文件嵌入工具

这个项目提供了多种方法来生成包含多个自定义命名文件的TNEF格式文件。

## 方法1：单个TNEF文件中的多个附件（推荐）

使用`tnef_creator_multi_v3.py`脚本创建一个包含多个自定义命名文件的TNEF文件。这是最推荐的方法，可以与标准TNEF提取工具兼容。

### 使用方法

```bash
python tnef_creator_multi_v3.py -a "文件1.txt:自定义名称1.txt" -a "文件2.txt:自定义名称2.txt" -o winmail.dat
```

这将创建一个包含两个嵌入文件的TNEF文件，文件名分别为"自定义名称1.txt"和"自定义名称2.txt"。

### 提取文件

```bash
tnef --number-backups winmail.dat
```

这将提取TNEF文件中的所有嵌入文件，并使用自定义名称保存。

## 方法2：多个TNEF文件

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

## 方法3：简化的多文件方法

使用`tnef_creator_multi_simple.py`脚本创建多个TNEF文件，并提供一个批处理脚本来提取所有文件。

### 使用方法

```bash
python tnef_creator_multi_simple.py -a "文件1.txt:自定义名称1.txt" -a "文件2.txt:自定义名称2.txt" -o tnef_files_simple -p tnef_simple
```

这将在`tnef_files_simple`目录中创建多个TNEF文件，并生成一个`extract_all.sh`脚本来提取所有文件。

### 提取文件

```bash
cd tnef_files_simple
./extract_all.sh
```

## 方法4：ZIP归档

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

## 技术细节

### TNEF格式

TNEF（Transport Neutral Encapsulation Format）是Microsoft Outlook和Exchange使用的一种专有格式，用于封装电子邮件附件。TNEF文件通常命名为"winmail.dat"，包含以下组件：

1. 文件头：TNEF签名（0x223e9f78）和16位随机密钥
2. 消息级属性：消息类、消息ID、主题、日期、正文等
3. 附件级属性：渲染数据、标题、传输文件名、创建/修改日期、数据等
4. 附件标记：用于分隔多个附件
5. 结束标记：表示TNEF文件的结束

### 多文件TNEF实现

`tnef_creator_multi_v3.py`脚本实现了在单个TNEF文件中嵌入多个文件的功能，并确保与标准TNEF提取工具兼容。关键技术点包括：

1. 正确的属性结构：确保每个属性都有正确的级别、ID、类型和数据
2. 属性长度处理：确保所有属性的长度大于4字节，这是TNEF提取工具的要求
3. 附件标记：使用正确的附件标记来分隔多个附件
4. MAPI属性：添加MAPI属性来确保与TNEF提取工具的兼容性

## 注意事项

- 方法1（单个TNEF文件中的多个附件）是最推荐的方法，可以与标准TNEF提取工具兼容。
- 方法2和方法3（多个TNEF文件）也是可靠的方法，但需要额外的步骤来提取所有文件。
- 方法4（ZIP归档）提供了一种更紧凑的方式来嵌入多个文件，但需要额外的步骤来提取文件。
- 所有方法都支持自定义嵌入文件的名称，这对于隐藏原始文件名或提供更有意义的文件名非常有用。

