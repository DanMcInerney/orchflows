# csvmerge — exhibited transcripts

Three recorded runs of the shipped tool. Each transcript is one fenced
JSON block: the argv after the program name, the exact input file
bytes, the exact stdout bytes, and the exit status. These transcripts
are licensed oracle material: a produced benchmark must anchor at
least one oracle to one of them or record why that is impossible.

```json
{
  "id": "t1",
  "argv": ["a.csv", "b.csv"],
  "files": {
    "a.csv": "1,alpha\n3,gamma\n5,epsilon\n",
    "b.csv": "2,beta\n3,delta\n"
  },
  "stdout": "1,alpha\n2,beta\n3,gamma\n5,epsilon\n",
  "exit": 0
}
```

```json
{
  "id": "t2",
  "argv": ["--prefer", "b", "a.csv", "b.csv"],
  "files": {
    "a.csv": "1,alpha\n4,delta\n",
    "b.csv": "4,dee\n9,zeta\n"
  },
  "stdout": "1,alpha\n4,dee\n9,zeta\n",
  "exit": 0
}
```

```json
{
  "id": "t3",
  "argv": ["a.csv", "b.csv"],
  "files": {
    "a.csv": "5,epsilon\n2,beta\n",
    "b.csv": "1,alpha\n"
  },
  "stdout": "",
  "exit": 1
}
```
