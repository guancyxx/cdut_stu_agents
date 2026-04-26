# Custom Problem Template Documentation

## Architecture

QDUOJ uses a three-section template format with `//PREPEND BEGIN...END`, `//TEMPLATE BEGIN...END`, `//APPEND BEGIN...END` markers:

```
//PREPEND BEGIN
#include <stdio.h>            ← hidden: includes & imports
//PREPEND END

//TEMPLATE BEGIN
int solve(int n) { ... }      ← visible in student editor: pure function
//TEMPLATE END

//APPEND BEGIN
int main(void) { ... }        ← hidden: I/O driver, calls solve()
//APPEND END
```

### Judging Flow

```
[Student submits code from editor]
         ↓
Dispatcher:  prepend + student_code + append  →  compiled binary
         ↓
Judge runner:  binary executed with stdin redirected from test case input
         ↓
Output comparison:  MD5(user_output.rstrip()) == MD5(expected_output.rstrip())
```

### Design Principles

1. **TEMPLATE = pure function only**: `solve()` accepts typed parameters and returns a value
2. **APPEND handles all I/O**: reading stdin, calling `solve()`, printing result
3. **PREPEND = imports/includes only**: no logic
4. **Every solve() has an `// Example:` comment** showing real test case data

---

## Problem Templates

### 1. Sum of Digits (`custom-uyga`)

| Input | Output |
|-------|--------|
| `12345` | `15` |

```c
int solve(int n) {
    // Example: solve(12345) → 15
    // TODO: return sum of digits of n
    return 0;
}
```

```python
def solve(n: int) -> int:
    # Example: solve(12345) → 15
    # TODO: return sum of digits of n
    return 0
```

---

### 2. Vowel Count (`custom-zjq5`)

| Input | Output |
|-------|--------|
| `HelloWorld` | `3` |

```c
int solve(char s[]) {
    // Example: solve("HelloWorld") → 3
    // TODO: return number of vowels (a e i o u, case-insensitive)
    return 0;
}
```

```python
def solve(s: str) -> int:
    # Example: solve('HelloWorld') → 3
    # TODO: return number of vowels in s
    return 0
```

---

### 3. Leap Year (`custom-yld9`)

| Input | Output |
|-------|--------|
| `2000` | `Yes` |
| `1900` | `No` |

```c
int solve(int y) {
    // Example: solve(2000) → 1 (Yes), solve(1900) → 0 (No)
    // TODO: return 1 if y is a leap year, else 0
    return 0;
}
```

```python
def solve(y: int) -> bool:
    # Example: solve(2000) → True, solve(1900) → False
    # TODO: return True if y is a leap year
    return False
```

---

### 4. Find the Maximum (`custom-8mld`)

| Input | Output |
|-------|--------|
| `5`<br>`3 7 2 7 1` | `7 2` |

```c
void solve(int arr[], int n, int *maxVal, int *pos) {
    // Example: arr=[3,7,2,7,1] n=5 → maxVal=7, pos=2
    // TODO: set *maxVal to maximum, *pos to its 1-indexed position
}
```

```cpp
pair<int,int> solve(vector<int>& a) {
    // Example: a=[3,7,2,7,1] → {7, 2}
    // TODO: return {max_value, 1-indexed_position}
    return {0, 0};
}
```

```java
public static int[] solve(int[] a) {
    // Example: a=[3,7,2,7,1] → [7, 2]
    // TODO: return new int[]{max_value, 1-indexed_position}
    return new int[]{0, 0};
}
```

```python
def solve(a: list) -> tuple:
    # Example: a=[3,7,2,7,1] → (7, 2)
    # TODO: return (max_value, 1-indexed_position)
    return (0, 1)
```

---

### 5. Caesar Cipher (`custom-adxc`)

| Input | Output |
|-------|--------|
| `3`<br>`HELLO` | `KHOOR` |

```c
void solve(char s[], int k) {
    // Example: s="HELLO" k=3 → modify s to "KHOOR"
    // TODO: apply Caesar shift k to each uppercase letter
}
```

```python
def solve(s: str, k: int) -> str:
    # Example: s='HELLO' k=3 → 'KHOOR'
    # TODO: return Caesar-shifted string
    return s
```

---

### 6. GCD of Multiple Numbers (`custom-95gv`)

| Input | Output |
|-------|--------|
| `3`<br>`12 18 24` | `6` |

```c
int solve(int arr[], int n) {
    // Example: arr=[12,18,24] n=3 → 6
    // TODO: return GCD of all numbers in arr
    return 1;
}
```

```python
def solve(a: list) -> int:
    # Example: a=[12,18,24] → 6
    # TODO: return GCD of all numbers in a
    return 1
```

---

### 7. Sort and Remove Duplicates (`custom-8ag3`)

| Input | Output |
|-------|--------|
| `8`<br>`3 1 2 3 1 5 2 4` | `5`<br>`1 2 3 4 5` |

```c
int solve(int arr[], int n, int out[]) {
    // Example: arr=[3,1,2,3,1,5,2,4] n=8 → out=[1,2,3,4,5], return 5
    // TODO: fill out[] with sorted unique values, return count
    return 0;
}
```

```python
def solve(a: list) -> list:
    # Example: a=[3,1,2,3,1,5,2,4] → [1,2,3,4,5]
    # TODO: return sorted list of unique values
    return []
```

---

### 8. Coin Change (`custom-3cdp`)

| Input | Output |
|-------|--------|
| `620` | `4` |

```c
int solve(long long A) {
    // Example: solve(620) → 4  (coins: [1,5,10,20,100])
    // TODO: return minimum number of coins
    return 0;
}
```

```python
def solve(A: int) -> int:
    # Example: solve(620) → 4
    # TODO: return minimum number of coins
    return 0
```

---

### 9. Climbing Stairs (`custom-2e2t`)

| Input | Output |
|-------|--------|
| `2` | `2` |
| `3` | `3` |

```c
long long solve(int n) {
    // Example: solve(2) → 2, solve(3) → 3
    // TODO: return number of ways to climb n stairs (1 or 2 steps)
    // Answer fits in 64-bit
    return 0;
}
```

```python
def solve(n: int) -> int:
    # Example: solve(2) → 2, solve(3) → 3
    # TODO: return number of ways to climb n stairs (1 or 2 steps)
    return 0
```

---

### 10. Subarray Sum Query (`custom-hkcr`)

| Input | Output |
|-------|--------|
| `5`<br>`1 2 3 4 5`<br>`3`<br>`1 3`<br>`2 5`<br>`4 4` | `6`<br>`14`<br>`4` |

```c
long long solve(long long prefix[], int l, int r) {
    // Example: l=1 r=3 → 6, l=2 r=5 → 14, l=4 r=4 → 4
    // TODO: return sum from index l to r (1-indexed)
    return 0;
}
```

```python
def solve(prefix: list, l: int, r: int) -> int:
    # Example: l=1 r=3 → 6, l=2 r=5 → 14, l=4 r=4 → 4
    # TODO: return sum from index l to r (1-indexed)
    return 0
```

---

## Full Template Examples (all 4 languages)

### Sum of Digits — complete C template as stored in DB

```
//PREPEND BEGIN
#include <stdio.h>
//PREPEND END

//TEMPLATE BEGIN
int solve(int n) {
    // Example: solve(12345) → 15
    // TODO: return sum of digits of n
    return 0;
}
//TEMPLATE END

//APPEND BEGIN
int main(void) {
    int n; scanf("%d", &n);
    printf("%d\n", solve(n));
    return 0;
}
//APPEND END
```

### Sum of Digits — complete Python3 template

```
//PREPEND BEGIN

//PREPEND END

//TEMPLATE BEGIN
def solve(n: int) -> int:
    # Example: solve(12345) → 15
    # TODO: return sum of digits of n
    return 0
//TEMPLATE END

//APPEND BEGIN
if __name__ == '__main__':
    n = int(input())
    print(solve(n))
//APPEND END
```

> **Note**: QDUOJ's `parse_problem_template` regex only matches `//` comment markers; all languages including Python3 must use `//PREPEND BEGIN` etc.

---

## Environment

| Component | Value |
|-----------|-------|
| OJ Backend | `registry.cn-hongkong.aliyuncs.com/oj-image/backend:1.6.1` |
| OJ Judge | `registry.cn-hongkong.aliyuncs.com/oj-image/judge:1.6.1` |
| PostgreSQL | `cdut-oj-postgres` (postgres:10-alpine) |
| I/O Mode | All 10 custom problems use Standard IO (stdin/stdout) |
| Rule Type | ACM |
| Languages | C, C++, Java, Python3 |
| Total Score | 0 (unscored practice problems) |

## Problem Metadata

| Display ID | DB ID | Title | Difficulty | Source | Time | Memory |
|------------|-------|-------|------------|--------|------|--------|
| custom-uyga | 1 | Sum of Digits | Low | Custom | 1000ms | 256MB |
| custom-zjq5 | 2 | Vowel Count | Low | Custom | 1000ms | 256MB |
| custom-yld9 | 3 | Leap Year | Low | Custom | 1000ms | 256MB |
| custom-8mld | 4 | Find the Maximum | Low | Custom | 1000ms | 256MB |
| custom-adxc | 5 | Caesar Cipher | Low | Custom | 1000ms | 256MB |
| custom-95gv | 6 | GCD of Multiple Numbers | Mid | Custom | 1000ms | 256MB |
| custom-8ag3 | 7 | Sort and Remove Duplicates | Mid | Custom | 2000ms | 256MB |
| custom-3cdp | 8 | Coin Change (Minimum Coins) | Mid | Custom | 1000ms | 256MB |
| custom-2e2t | 9 | Climbing Stairs | Mid | Custom | 1000ms | 256MB |
| custom-hkcr | 10 | Subarray Sum Query | Mid | Custom | 2000ms | 256MB |
