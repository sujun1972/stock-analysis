---
name: smart-commit
description: 智能提交：只提交对话过程中修改的文件，自动排除其他人的改动
user-invocable: true
disable-model-invocation: false
---

# 智能 Git Commit (Smart Commit)

你是一个智能的 Git 提交助手，负责只提交当前 Claude Code 对话过程中产生、修改或删除的文件，**不会加入其他人修改的文件**。

## 核心原则

1. **只提交对话相关的文件** - 仅提交本次对话中 Claude 创建、修改或删除的文件
2. **排除他人改动** - 自动识别并排除其他开发者的修改
3. **智能分析** - 分析文件修改时间、内容关联性，确定哪些文件属于本次对话
4. **安全第一** - 在提交前展示将要提交的文件列表，让用户确认

## 执行步骤

### 第一步：获取当前会话的开始时间

```bash
cd /Volumes/MacDriver/stock-analysis

# 记录当前时间（会话结束时间）
SESSION_END_TIME=$(date +%s)

# 向用户询问会话开始的大致时间（分钟前）
# 默认假设会话在 30 分钟前开始
SESSION_DURATION_MINUTES=30

# 计算会话开始时间戳
SESSION_START_TIME=$((SESSION_END_TIME - SESSION_DURATION_MINUTES * 60))

echo "会话时间窗口："
echo "  开始: $(date -r $SESSION_START_TIME '+%Y-%m-%d %H:%M:%S')"
echo "  结束: $(date -r $SESSION_END_TIME '+%Y-%m-%d %H:%M:%S')"
```

### 第二步：分析 Git 状态

```bash
echo -e "\n================================================================================"
echo "                         Git 状态分析"
echo "================================================================================"

# 显示当前分支
echo -e "\n当前分支:"
git branch --show-current

# 显示所有未提交的改动
echo -e "\n所有未提交的改动:"
git status --short

# 统计改动的文件数量
total_modified=$(git status --short | wc -l | xargs)
echo -e "\n改动文件总数: $total_modified"
```

### 第三步：识别对话中修改的文件

```bash
echo -e "\n================================================================================"
echo "                    识别对话过程中修改的文件"
echo "================================================================================"

# 创建临时文件存储分析结果
CONVERSATION_FILES="/tmp/claude_conversation_files_$$.txt"
OTHER_FILES="/tmp/claude_other_files_$$.txt"

> "$CONVERSATION_FILES"
> "$OTHER_FILES"

# 分析每个修改的文件
echo -e "\n分析文件修改时间..."

for file in $(git status --short | awk '{print $2}'); do
    if [ -f "$file" ]; then
        # 获取文件的最后修改时间
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            FILE_MTIME=$(stat -f %m "$file")
        else
            # Linux
            FILE_MTIME=$(stat -c %Y "$file")
        fi

        # 判断文件是否在会话时间窗口内修改
        if [ $FILE_MTIME -ge $SESSION_START_TIME ]; then
            echo "$file" >> "$CONVERSATION_FILES"
            echo "  ✅ $file (修改于 $(date -r $FILE_MTIME '+%H:%M:%S'))"
        else
            echo "$file" >> "$OTHER_FILES"
            echo "  ⏸️  $file (修改于 $(date -r $FILE_MTIME '+%m-%d %H:%M'), 不在会话窗口内)"
        fi
    else
        # 文件已删除，检查 git status 看是否是删除操作
        if git status --short | grep "^ D" | grep -q "$file"; then
            # 假设删除操作是在会话中进行的
            echo "$file" >> "$CONVERSATION_FILES"
            echo "  🗑️  $file (已删除)"
        fi
    fi
done
```

### 第四步：显示分类结果

```bash
echo -e "\n================================================================================"
echo "                         文件分类结果"
echo "================================================================================"

# 显示将要提交的文件
conversation_count=$(wc -l < "$CONVERSATION_FILES" | xargs)
other_count=$(wc -l < "$OTHER_FILES" | xargs)

echo -e "\n📦 将要提交的文件 (本次对话修改，共 $conversation_count 个):"
if [ $conversation_count -gt 0 ]; then
    cat "$CONVERSATION_FILES" | while read file; do
        # 显示文件状态
        status=$(git status --short "$file" | awk '{print $1}')
        case $status in
            M) echo "  📝 修改: $file" ;;
            A) echo "  ➕ 新增: $file" ;;
            D) echo "  ❌ 删除: $file" ;;
            ??) echo "  ✨ 未跟踪: $file" ;;
            *) echo "  📄 $file" ;;
        esac
    done
else
    echo "  (无)"
fi

echo -e "\n⏸️  排除的文件 (其他人修改或会话外修改，共 $other_count 个):"
if [ $other_count -gt 0 ]; then
    cat "$OTHER_FILES" | while read file; do
        echo "  ⊘  $file"
    done
else
    echo "  (无)"
fi
```

### 第五步：显示将要提交的文件内容变更

```bash
echo -e "\n================================================================================"
echo "                         文件变更详情"
echo "================================================================================"

if [ $conversation_count -gt 0 ]; then
    echo -e "\n查看将要提交的文件的改动详情:\n"

    cat "$CONVERSATION_FILES" | while read file; do
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "文件: $file"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # 检查文件状态
        if [ -f "$file" ]; then
            # 文件存在，显示 diff
            if git ls-files --error-unmatch "$file" &> /dev/null; then
                # 文件已被 Git 跟踪
                git diff HEAD "$file" | head -100
            else
                # 新文件
                echo "新文件，前 20 行内容:"
                head -20 "$file"
            fi
        else
            # 文件已删除
            echo "文件已删除"
        fi
        echo ""
    done
fi
```

### 第六步：生成提交信息

```bash
echo -e "\n================================================================================"
echo "                         生成提交信息"
echo "================================================================================"

# 分析改动类型
added_count=$(cat "$CONVERSATION_FILES" | while read f; do git status --short "$f"; done | grep -c "^A" || echo 0)
modified_count=$(cat "$CONVERSATION_FILES" | while read f; do git status --short "$f"; done | grep -c "^ M\|^M" || echo 0)
deleted_count=$(cat "$CONVERSATION_FILES" | while read f; do git status --short "$f"; done | grep -c "^ D\|^D" || echo 0)
untracked_count=$(cat "$CONVERSATION_FILES" | while read f; do git status --short "$f"; done | grep -c "^??" || echo 0)

echo -e "\n变更统计:"
echo "  新增文件: $added_count"
echo "  修改文件: $modified_count"
echo "  删除文件: $deleted_count"
echo "  未跟踪文件: $untracked_count"

# 根据改动生成合适的提交信息前缀
if [ $added_count -gt 0 ] && [ $modified_count -eq 0 ] && [ $deleted_count -eq 0 ]; then
    COMMIT_PREFIX="feat"
elif [ $modified_count -gt 0 ] && [ $added_count -eq 0 ]; then
    COMMIT_PREFIX="refactor"
elif [ $deleted_count -gt 0 ]; then
    COMMIT_PREFIX="refactor"
else
    COMMIT_PREFIX="chore"
fi

echo -e "\n建议的提交类型: $COMMIT_PREFIX"
```

### 第七步：询问用户确认并执行提交

```bash
echo -e "\n================================================================================"
echo "                         准备提交"
echo "================================================================================"

if [ $conversation_count -eq 0 ]; then
    echo "❌ 没有检测到对话过程中修改的文件，无需提交。"
    exit 0
fi

echo -e "\n即将提交 $conversation_count 个文件。"
echo ""
echo "请输入提交信息（不包括类型前缀，将自动添加 '$COMMIT_PREFIX:' 前缀）:"
echo "示例: '优化日志系统检查逻辑' 将变成 '$COMMIT_PREFIX: 优化日志系统检查逻辑'"
echo ""
echo "或者直接按 Enter 使用自动生成的提交信息。"
```

## 用户交互流程

此 skill 需要与用户进行以下交互：

1. **确认会话时长** - 询问用户本次对话大约开始于多少分钟前（默认 30 分钟）
2. **显示文件列表** - 展示将要提交和排除的文件清单
3. **显示变更内容** - 展示每个文件的改动详情（diff）
4. **确认提交** - 询问用户是否确认提交这些文件
5. **输入提交信息** - 让用户输入或确认提交信息

## 智能识别逻辑

### 判断文件是否属于本次对话的标准：

1. **时间窗口匹配** ✅
   - 文件的最后修改时间在会话开始时间之后
   - 默认会话窗口为 30 分钟，可由用户调整

2. **文件类型相关性** ✅
   - 如果是 `.claude/skills/` 目录下的文件，大概率是本次对话相关
   - 如果是测试文件且最近修改，可能相关

3. **Git 状态** ✅
   - 新增的未跟踪文件（`??`）优先视为本次对话创建
   - 暂存区的文件（staged）需要特别注意

4. **排除规则** ⛔
   - 修改时间明显早于会话开始的文件
   - 位于 `.git/` 等特殊目录的文件
   - 自动生成的文件（如编译产物）

## 提交信息规范

遵循项目的 Git commit 规范：

```
<type>: <subject>

<body (optional)>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 提交类型 (type)

根据改动自动判断：

- `feat` - 新增功能或文件
- `fix` - 修复 bug
- `refactor` - 重构代码
- `docs` - 文档更新
- `test` - 测试相关
- `chore` - 其他杂项（构建、配置等）
- `style` - 代码格式调整

## 实际执行提交

在用户确认后，执行以下命令：

```bash
# 添加对话中修改的文件
cat "$CONVERSATION_FILES" | while read file; do
    git add "$file"
done

# 生成完整的提交信息
COMMIT_MESSAGE="$COMMIT_PREFIX: $USER_INPUT

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 执行提交
git commit -m "$COMMIT_MESSAGE"

# 显示提交结果
echo -e "\n✅ 提交成功！"
echo ""
git log -1 --stat

# 清理临时文件
rm -f "$CONVERSATION_FILES" "$OTHER_FILES"
```

## 安全检查

在提交前，自动进行以下检查：

### 1. 敏感文件检查

```bash
# 检查是否包含敏感文件
SENSITIVE_PATTERNS=(.env .credentials.json .secret .key id_rsa .pem)

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if cat "$CONVERSATION_FILES" | grep -q "$pattern"; then
        echo "⚠️  警告: 检测到可能包含敏感信息的文件: $pattern"
        echo "请仔细检查后再提交！"
    fi
done
```

### 2. 大文件检查

```bash
# 检查是否包含大文件（>10MB）
echo -e "\n检查大文件..."
cat "$CONVERSATION_FILES" | while read file; do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        if [ $size -gt 10485760 ]; then
            size_mb=$((size / 1048576))
            echo "⚠️  警告: $file 大小为 ${size_mb}MB，超过 10MB"
        fi
    fi
done
```

### 3. 冲突检查

```bash
# 检查是否有合并冲突标记
echo -e "\n检查冲突标记..."
cat "$CONVERSATION_FILES" | while read file; do
    if [ -f "$file" ]; then
        if grep -q "<<<<<<< HEAD" "$file"; then
            echo "❌ 错误: $file 包含未解决的合并冲突"
            exit 1
        fi
    fi
done
```

## 使用示例

### 场景 1：对话中修改了多个文件

```
用户: /skill smart-commit

Claude:
分析 Git 状态...
检测到 15 个修改的文件

📦 将要提交的文件 (本次对话修改，共 3 个):
  📝 修改: .claude/skills/check-logging/skill.md
  📝 修改: .claude/skills/check-logging/README.md
  ✨ 未跟踪: .claude/skills/smart-commit/skill.md

⏸️  排除的文件 (其他人修改，共 12 个):
  ⊘  core/src/providers/akshare/provider.py
  ⊘  core/src/providers/tushare/metrics.py
  ...

即将提交 3 个文件。
请输入提交信息: 添加智能提交 skill

✅ 提交成功！
```

### 场景 2：没有对话相关的改动

```
用户: /skill smart-commit

Claude:
分析 Git 状态...
检测到 8 个修改的文件

📦 将要提交的文件 (本次对话修改，共 0 个):
  (无)

⏸️  排除的文件 (其他人修改，共 8 个):
  ⊘  core/src/providers/akshare/provider.py
  ...

❌ 没有检测到对话过程中修改的文件，无需提交。
```

## 高级选项

### 手动指定会话时长

用户可以在调用时指定会话开始时间：

```bash
# 会话开始于 60 分钟前
SESSION_DURATION_MINUTES=60
```

### 强制包含特定文件

如果时间判断不准确，用户可以手动指定要包含的文件：

```bash
# 在确认阶段，用户可以手动添加文件
git add <file_path>
```

### 排除特定文件

用户可以手动取消某些文件的暂存：

```bash
git reset HEAD <file_path>
```

## 注意事项

1. **时间判断的局限性** - 基于文件修改时间的判断可能不够准确，特别是：
   - 文件被编辑器自动保存
   - 系统时间不准确
   - 使用了格式化工具自动修改文件

2. **用户确认很重要** - 始终在提交前展示文件列表和变更内容，让用户最终确认

3. **不会自动 push** - 此 skill 只执行本地 commit，不会自动推送到远程仓库

4. **适用于独立分支** - 在多人协作的共享分支上使用时需要特别小心

## 相关文档

- [Git 提交规范](../../../docs/git-workflow.md)
- [代码审查 skill](../code-review/skill.md)
- [Pro Git Book](https://git-scm.com/book/en/v2)

## 故障排除

### Q: 如何调整会话时间窗口？

A: 修改 `SESSION_DURATION_MINUTES` 变量，单位为分钟。

### Q: 某个文件应该提交但被排除了怎么办？

A: 可以在确认阶段手动使用 `git add <file>` 添加该文件。

### Q: 误提交了不该提交的文件怎么办？

A: 使用 `git reset HEAD~1` 撤销最后一次提交（不会删除文件改动）。

### Q: 如何查看完整的 diff？

A: 在提交前，可以使用 `git diff` 查看所有改动。
