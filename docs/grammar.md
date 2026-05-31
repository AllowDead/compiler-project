Program ::= { Declaration }
## 2. Declarations
Declaration ::= FunctionDecl | StructDecl | VarDecl

FunctionDecl   ::= "fn" Identifier "(" [ Parameters ] ")" Type Block

StructDecl ::= "struct" Identifier "{" { VarDecl } "}"

VarDecl ::= Type Identifier [ "=" Expression ] ";"

Parameters ::= Parameter { "," Parameter }
Parameter ::= Identifier Type


## 3. Statements
Statement ::= Block | IfStmt | WhileStmt | ForStmt | ReturnStmt
| ExprStmt | VarDecl

Block ::= "{" { Statement } "}"

IfStmt ::= "if" "(" Expression ")" Statement [ "else" Statement ]

WhileStmt ::= "while" "(" Expression ")" Statement

ForStmt ::= "for" "(" [ ExprStmt ] ";" [ Expression ] ";" [ Expression ] ")" Statement

ReturnStmt ::= "return" [ Expression ] ";"

ExprStmt ::= Expression ";"

## 4. Expressions (Precedence: Lowest to Highest)

Expression ::= Assignment

Assignment ::= LogicalOr { ("=" | "+=" | "-=" | "*=" | "/=" | "%=") Assignment }

LogicalOr ::= LogicalAnd { "||" LogicalAnd }

LogicalAnd ::= Equality { "&&" Equality }

Equality ::= Relational { ("==" | "!=") Relational }

Relational ::= Additive { ("<" | "<=" | ">" | ">=") Additive }

Additive ::= Multiplicative { ("+" | "-") Multiplicative }

Multiplicative ::= Unary { ("*" | "/" | "%") Unary }

Unary ::= ("-" | "!") Unary | Primary

Primary ::= Literal | Identifier | "(" Expression ")" | Call

Call ::= Identifier "(" [ Arguments ] ")"

Arguments ::= Expression { "," Expression }

## 5. Types and Literals

Type ::= "int" | "float" | "bool" | "void" | Identifier

Literal ::= Integer | Float | String | Boolean


## 6. Operator Precedence & Associativity

| Level | Operators | Associativity |
|-------|-----------|---------------|
| 8 | `=` `+=` `-=` `*=` `/=` `%=` | Right |
| 7 | `||` | Left |
| 6 | `&&` | Left |
| 5 | `==` `!=` | Non-associative |
| 4 | `<` `<=` `>` `>=` | Non-associative |
| 3 | `+` `-` | Left |
| 2 | `*` `/` `%` | Left |
| 1 | `-` `!` | Right |
| 0 | `()` `.` `[]` (Call/Access) | Left |
