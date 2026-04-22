# OJ 题库基础代码模板建设方案

> For Hermes: this is a planning document for introducing starter-code templates into the current OJ problem set.

## 一、目标

为当前 OJ 题库补充“基础代码结构 / starter code / 代码模板”能力，让用户在进入题目后，不必从完全空白编辑器开始输入，而是能够根据所选语言自动获得最小可运行骨架代码。

本方案重点解决以下问题：

1. 当前 609 道题的 `template` 字段全部为空。
2. 用户提交区默认是空白编辑器，基础教学题体验较差。
3. 初学者容易因为 main 函数、输入输出框架、类名或语言入口格式错误而提交失败。
4. 题库中不少题目本身是入门题、例题、练习题，天然适合提供 starter code。

## 二、现状结论

已经完成真实检查，结果如下：

- 题目总数：609
- `template` 非空题目数：0
- 前台题目页编辑器默认无基础代码
- 当前“示例代码”仅零散存在于部分题目的 `hint` 中，不是结构化模板，也不会自动带入编辑器

因此，当前系统实际上“不提供基础代码结构”。

## 三、建设目标

### 1. 用户目标

- 打开题目后，选择语言即可看到该语言的最小运行模板。
- 对新手友好的题目可直接提供更贴近题意的 starter code。
- 降低因为语言入口、类名、输入输出格式不熟悉导致的非算法性错误。

### 2. 系统目标

- 使用现有 `Problem.template` 字段承载模板数据。
- 保持与当前 OJ 后端逻辑兼容，不改变判题主链路。
- 支持按题目、按语言精细化配置模板。
- 支持分阶段上线：先做通用模板，再做题目特化模板。

## 四、总体方案

建议采用“两层模板体系”。

### 层级 A：全局语言默认模板

作用：
- 为所有题目提供统一的最小可运行骨架。
- 即使某道题没有专门模板，用户也不会看到完全空白编辑器。

适用语言建议：
- C
- C++
- Java
- Python3
- Golang
- JavaScript

示例：
- C：`int main() { return 0; }`
- C++：`int main() { return 0; }`
- Java：`public class Main { public static void main(String[] args) { } }`
- Python3：读 stdin 的最小入口
- Golang：`package main` + `func main()`
- JavaScript：Node.js stdin 模板

### 层级 B：题目级语言模板

作用：
- 对基础教学题、格式固定题、函数骨架题提供更贴近题意的模板。
- 例如数组输入题、单组整数输入题、多组数据题、大整数题等，可以提供更符合该题的读取结构。

适用范围建议：
- 入门题
- 例题/练习题
- 高频使用题
- 对语言入口要求敏感的题目
- 未来若有 Template Problem，可继续复用该机制

优先策略：
- 先实现全局默认模板
- 再针对一批典型题目补题目级模板

## 五、模板设计原则

### 1. 模板必须“最小且正确”

要求：
- 能直接编译/运行
- 不包含多余逻辑
- 不预置错误示例
- 不加入与题目无关的注释噪音

### 2. 模板必须适配 OJ 运行环境

要求：
- Java 使用 `Main` 类名
- 输入输出统一走标准输入输出
- 不读写文件
- 不依赖本地环境特性

### 3. 模板必须便于初学者修改

要求：
- 结构清晰
- 留出显式解题区域
- 不要过度抽象

### 4. 代码注释统一英文

依据当前项目约束：
- 代码中不允许出现中文注释
- 若模板含注释，只能使用英文注释

## 六、推荐模板规范

### 1. 通用模板示例

#### C

```c
#include <stdio.h>

int main(void) {
    return 0;
}
```

#### C++

```cpp
#include <iostream>
using namespace std;

int main() {
    return 0;
}
```

#### Java

```java
import java.util.*;

public class Main {
    public static void main(String[] args) {
    }
}
```

#### Python3

```python
import sys


def solve() -> None:
    pass


if __name__ == "__main__":
    solve()
```

#### Golang

```go
package main

func main() {
}
```

#### JavaScript

```javascript
'use strict';

function solve(input) {
}

const fs = require('fs');
const input = fs.readFileSync(0, 'utf8');
solve(input);
```

### 2. 题目级模板示例

以 A+B 题为例：

#### Python3

```python
import sys


def solve() -> None:
    a, b = map(int, sys.stdin.readline().split())
    print(a + b)


if __name__ == "__main__":
    solve()
```

#### Java

```java
import java.util.*;

public class Main {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        int a = scanner.nextInt();
        int b = scanner.nextInt();
        System.out.println(a + b);
    }
}
```

说明：
- 这种题目级模板更适合最基础教学题。
- 但不建议一次性给所有题目都写“接近答案”的模板，否则维护成本高，且容易削弱训练价值。

## 七、题目分层策略

建议把题目分成三层处理。

### 第一层：只提供全局通用模板

适用于：
- 大多数普通 ACM 题
- 不需要固定输入骨架的题
- 中高难度题

处理方式：
- 不写 `Problem.template`
- 前端按语言自动显示系统默认 starter code

### 第二层：提供题目级基础模板

适用于：
- 入门题
- 格式固定题
- 例题、练习题
- 教学导向题

处理方式：
- 在 `Problem.template` 中按语言写入基础结构
- 模板可包含基础输入读取框架
- 但不应包含完整解法

### 第三层：特殊模板题

适用于：
- 未来的函数题 / 填空题 / Template Problem
- 需要 `prepend/append` 的题型

处理方式：
- 单独设计模板结构
- 与当前普通 ACM 题模板能力解耦

## 八、实施路径

### 阶段 1：建立默认模板能力（推荐最先做）

目标：
- 让所有题目至少都有语言默认骨架

实施内容：
1. 梳理前端题目提交页当前编辑器初始化逻辑
2. 增加“语言 -> 默认模板”映射
3. 当题目 `template` 为空时，自动加载默认模板
4. 当题目 `template` 有值时，优先加载题目级模板
5. 验证切换语言时模板行为是否符合预期

优点：
- 改动集中
- 收益立竿见影
- 不需要先批量修改 609 道题的数据

### 阶段 2：为基础教学题补题目级模板

目标：
- 优先改善基础题用户体验

建议范围：
- 标题包含 `例`、`练` 的教学题
- 入门题、输入输出固定题
- 当前访问量高或新手常做题

实施内容：
1. 先筛一批约 50~100 题
2. 为 Python3 / C / C++ / Java 四种主语言补模板
3. 通过脚本批量写入 `Problem.template`
4. 回归检查前台展示与提交行为

### 阶段 3：建立模板治理机制

目标：
- 让后续导题/编题也能持续带模板

实施内容：
1. 后台编辑题目时支持管理模板
2. 导入脚本支持写入 `template`
3. 题库体检脚本增加“模板覆盖率”统计
4. 建立模板编写规范与审核要求

## 九、数据结构建议

建议沿用当前 `Problem.template` 字段的字典结构，按语言名存模板内容。

建议示例：

```json
{
  "C": "#include <stdio.h>\n\nint main(void) {\n    return 0;\n}\n",
  "C++": "#include <iostream>\nusing namespace std;\n\nint main() {\n    return 0;\n}\n",
  "Java": "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n    }\n}\n",
  "Python3": "import sys\n\n\ndef solve() -> None:\n    pass\n\n\nif __name__ == \"__main__\":\n    solve()\n"
}
```

如果后续要支持更复杂模板，可扩展为：

```json
{
  "Python3": {
    "mode": "editor_template",
    "code": "..."
  }
}
```

但当前阶段不建议过度设计，优先保持简单兼容。

## 十、风险与注意事项

### 1. 不要把“模板”做成“标准答案”

风险：
- 用户直接提交即可通过
- 降低训练价值

规避：
- 对多数题仅提供骨架和基本输入框架
- 不自动提供完整算法实现

### 2. 不同语言模板风格不统一

风险：
- 用户体验不一致
- 维护困难

规避：
- 先制定统一模板规范
- 每种语言使用固定风格

### 3. 切换语言时覆盖用户代码

风险：
- 用户已输入代码但切语言后被模板覆盖

规避：
- 若编辑器已有非空内容，切语言时必须二次确认
- 或仅在“首次选择语言”时自动注入模板

### 4. 模板与题目类型不匹配

风险：
- 模板误导用户
- 某些题不适合固定输入框架

规避：
- 默认模板尽量最小
- 特化模板只给真正适合的题目

## 十一、验收标准

方案落地后，至少应满足：

1. 打开任意题目，选择语言后，编辑器不再是完全空白。
2. 若题目存在 `template`，优先显示题目级模板。
3. 若题目不存在 `template`，显示系统默认模板。
4. Java 模板可直接通过编译入口约束。
5. 切换语言行为可预期，不会无提示覆盖用户代码。
6. 至少有一批基础题成功补充题目级 starter code。
7. 文档和体检脚本中可看到模板覆盖率统计。

## 十二、建议落地顺序

推荐按以下顺序执行：

1. 先实现前端“默认模板回退机制”
2. 再补一批基础教学题的题目级模板
3. 再建设导入规范、后台维护能力和体检脚本

这样可以先用最小改动解决“完全空白编辑器”的问题，再逐步提升题库模板质量。

## 十三、最终建议

建议立即启动“基础代码模板一期建设”，范围如下：

- 一期目标：所有题目支持语言默认 starter code
- 一期语言：C / C++ / Java / Python3 / Golang / JavaScript
- 二期目标：为基础题与教学题补题目级模板
- 二期配套：增加模板覆盖率审计和模板规范文档

这是一个低风险、高感知收益的改进项。

对当前 OJ 来说，它不会改变判题核心逻辑，但会明显提升：

- 新手体验
- 教学友好度
- 首次提交成功率
- 题库专业度
