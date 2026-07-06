# Test Solutions — Arbiter

Correct solutions for every problem, in both Python and C++. Every single one
below was actually submitted through the real running server and confirmed
to return **AC** before being put in this file — so if you paste one in and
get anything other than AC, something in your local setup (not the code) is
the thing to debug.

Paste one into the code box, pick the matching language in the dropdown, hit
Submit.

---

## Sum of Two Numbers (`sum-two-numbers`)

**Python**
```python
a = int(input())
b = int(input())
print(a + b)
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    int a, b;
    cin >> a >> b;
    cout << a + b;
    return 0;
}
```

---

## Reverse a String (`reverse-string`)

**Python**
```python
s = input()
print(s[::-1])
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    string s;
    getline(cin, s);
    reverse(s.begin(), s.end());
    cout << s;
    return 0;
}
```

---

## Check Prime (`is-prime`)

**Python**
```python
n = int(input())
if n < 2:
    print("NO")
else:
    ok = True
    i = 2
    while i * i <= n:
        if n % i == 0:
            ok = False
            break
        i += 1
    print("YES" if ok else "NO")
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    long long n;
    cin >> n;
    bool isPrime = (n >= 2);
    for (long long i = 2; i * i <= n && isPrime; i++) {
        if (n % i == 0) isPrime = false;
    }
    cout << (isPrime ? "YES" : "NO");
    return 0;
}
```

---

## Factorial (`factorial`)

**Python**
```python
n = int(input())
r = 1
for i in range(2, n + 1):
    r *= i
print(r)
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    long long n;
    cin >> n;
    long long r = 1;
    for (long long i = 2; i <= n; i++) r *= i;
    cout << r;
    return 0;
}
```

---

## Sum of an Array (`array-sum`)

**Python**
```python
n = int(input())
total = 0
for _ in range(n):
    total += int(input())
print(total)
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    int n;
    cin >> n;
    long long total = 0;
    for (int i = 0; i < n; i++) {
        long long x;
        cin >> x;
        total += x;
    }
    cout << total;
    return 0;
}
```

---

## Count Vowels (`count-vowels`)

**Python**
```python
s = input()
print(sum(1 for c in s.lower() if c in "aeiou"))
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    string s;
    getline(cin, s);
    int count = 0;
    for (char c : s) {
        c = tolower(c);
        if (c=='a' || c=='e' || c=='i' || c=='o' || c=='u') count++;
    }
    cout << count;
    return 0;
}
```

---

## Maximum in an Array (`max-in-array`)

**Python**
```python
n = int(input())
vals = [int(input()) for _ in range(n)]
print(max(vals))
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    int n;
    cin >> n;
    long long mx = LLONG_MIN;
    for (int i = 0; i < n; i++) {
        long long x;
        cin >> x;
        mx = max(mx, x);
    }
    cout << mx;
    return 0;
}
```

---

## Nth Fibonacci Number (`fibonacci-nth`)

**Python**
```python
n = int(input())
a, b = 0, 1
for _ in range(n):
    a, b = b, a + b
print(a)
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    int n;
    cin >> n;
    long long a = 0, b = 1;
    for (int i = 0; i < n; i++) {
        long long t = a + b;
        a = b;
        b = t;
    }
    cout << a;
    return 0;
}
```

---

## GCD of Two Numbers (`gcd-two-numbers`)

**Python**
```python
import math
a = int(input())
b = int(input())
print(math.gcd(a, b))
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    long long a, b;
    cin >> a >> b;
    cout << __gcd(a, b);
    return 0;
}
```

---

## Balanced Parentheses (`balanced-parentheses`)

**Python**
```python
s = input()
stack = []
pairs = {")": "(", "]": "[", "}": "{"}
ok = True
for c in s:
    if c in "([{":
        stack.append(c)
    elif c in ")]}":
        if not stack or stack.pop() != pairs[c]:
            ok = False
            break
print("YES" if ok and not stack else "NO")
```

**C++**
```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){
    string s;
    getline(cin, s);
    stack<char> st;
    bool ok = true;
    for (char c : s) {
        if (c=='(' || c=='[' || c=='{') {
            st.push(c);
        } else if (c==')' || c==']' || c=='}') {
            if (st.empty()) { ok = false; break; }
            char top = st.top(); st.pop();
            if ((c==')' && top!='(') || (c==']' && top!='[') || (c=='}' && top!='{')) {
                ok = false;
                break;
            }
        }
    }
    if (!st.empty()) ok = false;
    cout << (ok ? "YES" : "NO");
    return 0;
}
```

---

## If something other than AC shows up

- **WA**: the code ran fine but the output didn't match — check for typos if you retyped instead of pasting.
- **CE** on a C++ submission: your `g++` isn't finding something, or a stray character got mangled during copy-paste. Try `g++ --version` in your terminal to confirm the compiler itself works.
- **RE**: usually an unhandled edge case (empty input, etc.) — all of these were verified against the real test cases already, so a fresh RE here would be worth flagging.
- Stuck on **"Judging..."** forever: this used to happen with C++ when `g++` was missing — that specific bug is fixed now (see README.md's "C++ submissions on Windows" section). If you see it again, something new broke and it's worth reporting.
