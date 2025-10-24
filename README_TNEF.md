# TNEF文件生成器

这个项目提供了用于生成TNEF格式文件（通常称为winmail.dat）的工具，并允许自定义嵌入的文件名称。

## 什么是TNEF？

TNEF（Transport Neutral Encapsulation Format）是Microsoft Outlook和Microsoft Exchange Server使用的一种专有电子邮件附件格式。它通常以winmail.dat文件的形式出现，包含了富文本格式的电子邮件和附件。

## 项目文件

- `tnef_creator.py` - 基本的TNEF文件生成器
- `tnef_creator_v2.py` - 增强版TNEF文件生成器，提供更完整的TNEF属性支持
- `tnef_creator_v3.py` - 修复日期属性的TNEF文件生成器
- `tnef_creator_v4.py` - 进一步改进的TNEF文件生成器
- `tnef_creator_simple.py` - 简化版TNEF文件生成器
- `tnef_creator_compatible.py` - 最终兼容版TNEF文件生成器，支持`--number-backups`选项
- `extract_tnef.py` - 使用tnefparse库尝试提取TNEF文件
- `extract_tnef_manual.py` - 手动解析和提取TNEF文件的工具

## 使用方法

### 生成TNEF文件

```bash
python tnef_creator_compatible.py -f "自定义文件名.txt" -c 内容文件.txt -o 输出文件.dat
```

参数说明：
- `-f, --filename` - 要嵌入的自定义文件名（必需）
- `-c, --content` - 要嵌入的文件内容（可选，如果不提供将使用默认内容）
- `-o, --output` - 输出的TNEF文件名（可选，默认为winmail.dat）

### 提取TNEF文件

```bash
python extract_tnef_manual.py winmail.dat
```

这将从TNEF文件中提取嵌入的文件，并使用嵌入的自定义文件名保存。

或者，您也可以使用标准的TNEF提取工具：

```bash
tnef winmail.dat
```

如果您想在提取时避免覆盖现有文件，可以使用`--number-backups`选项：

```bash
tnef --number-backups winmail.dat
```

这将创建带有数字后缀的备份文件，而不是覆盖原有文件。

## TNEF文件结构

TNEF文件的基本结构如下：

1. TNEF签名（32位值，0x223e9f78）
2. 密钥（16位随机整数）
3. 消息级属性（如消息类、消息ID、主题、日期等）
4. 附件级属性（如渲染数据、标题、传输文件名、MIME类型、创建/修改日期、大小、数据等）

每个属性包含：
- 级别（消息或附件）
- 类型（字符串、文本、日期等）
- ID
- 长度
- 数据
- 校验和

## 示例

```bash
# 创建一个TNEF文件，嵌入的文件名为"secret_document.pdf"
python tnef_creator_compatible.py -f "secret_document.pdf" -c 实际文档.pdf

# 提取TNEF文件中的内容
python extract_tnef_manual.py winmail.dat
# 这将创建一个名为"secret_document.pdf"的文件
```

## 注意事项

- 生成的TNEF文件可能不被所有TNEF解析器识别，因为TNEF格式是专有的，没有完整的公开规范。
- 某些电子邮件客户端可能会自动处理TNEF附件，而其他客户端可能会显示为winmail.dat文件。
- 这个工具主要用于测试和教育目的。

