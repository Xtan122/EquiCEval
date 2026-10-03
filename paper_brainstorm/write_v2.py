content = r"""\documentclass[11pt,a4paper]{article}

\usepackage[margin=2.2cm]{geometry}
\usepackage{fontspec}
\setmainfont{Times New Roman}
\setmonofont[Scale=0.88]{Menlo}
\usepackage{polyglossia}
\setdefaultlanguage{vietnamese}
\usepackage{microtype}
\usepackage{mathtools,amssymb,amsmath}
\usepackage{booktabs,tabularx,array}
\usepackage{enumitem}
\usepackage{xspace,xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,shapes.geometric}
\usepackage[most]{tcolorbox}
\usepackage{graphicx}
\usepackage{csquotes}
\DeclareQuoteAlias{american}{vietnamese}
\usepackage[
  backend=biber, style=authoryear-comp, language=english,
  maxcitenames=2, maxbibnames=99, uniquelist=false,
  uniquename=init, giveninits=true, doi=true, url=true, isbn=false
]{biblatex}
\DeclareLanguageMapping{vietnamese}{english}
\addbibresource{equiceval_improvement.bib}
\usepackage[unicode,colorlinks=true,allcolors=blue!55!black]{hyperref}

% Colors
\definecolor{navy}{HTML}{17324D}
\definecolor{teal}{HTML}{0B7A75}
\definecolor{gold}{HTML}{C58B22}
\definecolor{brick}{HTML}{A33B20}
\definecolor{softblue}{HTML}{EAF2F8}
\definecolor{softgreen}{HTML}{E9F5F2}
\definecolor{softgold}{HTML}{FCF4E5}
\definecolor{softred}{HTML}{FBEDEA}
\definecolor{softyellow}{HTML}{FFFDE7}
\definecolor{gray6}{HTML}{4A5568}

% tcolorbox environments
\newtcolorbox{example}[1][]{
  enhanced,breakable,colback=softyellow,colframe=gold,boxrule=0.7pt,
  arc=2mm,left=3mm,right=3mm,top=2mm,bottom=2mm,
  fonttitle=\bfseries\small,title={Vi du minh hoa},#1}

\newtcolorbox{keyformula}[1][]{
  enhanced,breakable,colback=softgreen,colframe=teal,boxrule=0.8pt,
  arc=2mm,left=3mm,right=3mm,top=2mm,bottom=2mm,
  fonttitle=\bfseries\small,title={Cong thuc trong tam},#1}

\newtcolorbox{warningbox}[1][]{
  enhanced,breakable,colback=softred,colframe=brick,boxrule=0.7pt,
  arc=2mm,left=3mm,right=3mm,top=2mm,bottom=2mm,
  fonttitle=\bfseries\small,title={Luu y quan trong},#1}

\newtcolorbox{proposition}[1][]{
  enhanced,breakable,colback=softgreen,colframe=teal,boxrule=0.8pt,
  arc=2mm,left=3mm,right=3mm,top=2mm,bottom=2mm,
  fonttitle=\bfseries\small,title={De xuat cai tien},#1}

% Layout
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.6em}
\setlength{\emergencystretch}{3em}
\renewcommand{\arraystretch}{1.2}
\setlist[itemize]{leftmargin=1.4em,itemsep=0.3em,topsep=0.3em}
\setlist[enumerate]{leftmargin=1.6em,itemsep=0.35em,topsep=0.3em}
\setcounter{tocdepth}{2}

\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcommand{\method}{\textsf{\textbf{EquiCEval}}\xspace}

\title{\vspace{-1.0cm}
  \textbf{\color{navy}EquiCEval: \DJ{}anh gia thanh phan theo ngu nghia tuong duong\\
  cho mo hinh toi uu hoa do LLM sinh ra}\\[0.4em]
  \large\color{gray6} Tai lieu ky thuat chi tiet ---
  Phuong phap, Cong thuc va Vi du minh hoa
}
\author{\small Kieu Van Tuyen \quad $\cdot$ \quad Phien ban 2.0 --- 08/2026}
\date{}

\begin{document}
\maketitle
\tableofcontents
\newpage

%----------------------------------------------------------------------
\section{Tong quan va \DJ{}ong luc}
%----------------------------------------------------------------------

\subsection{Van de can giai quyet}

Khi su dung LLM de sinh ra mo hinh toi uu hoa (LP/MILP), ta can danh gia xem mo hinh
LLM co dung khong so voi mo hinh chuan (Ground Truth). Cach don gian nhat la
\emph{so khop chuoi ky tu} hoac dung \emph{Cons-RMSE}. Tuy nhien, cach nay co ba diem yeu:

\begin{enumerate}
  \item \textbf{Reference-form bias:} Hai rang buoc toan hoc tuong duong co the bi
  danh gia la ``sai'' chi vi viet theo cach khac
  (vi du: $3x+2y\leq6$ va $6x+4y\leq12$ la nhu nhau nhung RMSE $\neq 0$).

  \item \textbf{Coverage blind spot:} Cons-RMSE \emph{loai bo} cac rang buoc bi thieu
  khoi tinh toan; 100 random samples thuong khong cham vao vung sai khac nho gan bien.

  \item \textbf{Statistical fragility:} Tuong quan Pearson $r = 0.9229$ giua
  Cons-RMSE va optimality gap giam con $r = 0.1792$ khi loai mot outlier duy nhat.
\end{enumerate}

\begin{example}
\textbf{Tai sao Exact String Matching khong dung duoc?}

Cho hai rang buoc:
\[
c_1: \; 6x + 4y \leq 12 \qquad c_2: \; 3x + 2y \leq 6
\]
Mien nghiem cua $c_1$ va $c_2$ \emph{hoan toan trung nhau}, nhung:
\[
\text{Cons-RMSE}(c_1, c_2) = \sqrt{(6-3)^2 + (4-2)^2 + (12-6)^2} = \sqrt{49} = 7 \neq 0.
\]
Day la false positive: mo hinh LLM viet dung nhung bi tinh la sai.
\end{example}

%----------------------------------------------------------------------
\section{Ky hieu va Bai toan}
%----------------------------------------------------------------------

Mo hinh toi uu hoa:
\[
M = (X, D, f, \mathcal{C})
\]
Ground Truth $M^\star = (X^\star, D^\star, f^\star, \mathcal{C}^\star)$
va mo hinh LLM $\widehat{M} = (\widehat{X}, \widehat{D}, \widehat{f}, \widehat{\mathcal{C}})$.

Khong gian quyet dinh chung $\mathcal{Y}$ voi hai anh xa:
\[
\pi^\star : X^\star \to \mathcal{Y}, \qquad
\widehat{\pi} : \widehat{X} \to \mathcal{Y}.
\]

Cac tap nghiem kha thi so sanh trong mien gioi han $B \subseteq \mathcal{Y}$:
\[
P^\star = B \cap \{\pi^\star(x) : x \in F(M^\star)\},
\qquad
\widehat{P} = B \cap \{\widehat{\pi}(\hat{x}) : \hat{x} \in F(\widehat{M})\}.
\]

\begin{warningbox}
\method la \emph{reference-based framework}: no kiem tra quan he giua hai mo hinh
trong mien va tolerance da khai bao, nhung \textbf{khong chung minh} mo hinh GT
phan anh dung toan bo y dinh nguoi dung. Truong hop khong co verified projection
hoac solver khong dong duoc bound phai bao la \textbf{inconclusive}.
\end{warningbox}

%----------------------------------------------------------------------
\section{Mo-dun 0: Pre-check va State Machine}
%----------------------------------------------------------------------

Truoc khi chay bat ky metric nao, \method gan mot tuple trang thai:
\[
S = (S_{\mathrm{parse}},\; S_{\mathrm{map}},\; S_{\mathrm{feas}},\;
     S_{\mathrm{bound}},\; S_{\mathrm{solve}}).
\]

\begin{table}[htbp]
\centering
\caption{Cac trang thai trong evaluator state machine.}
\small
\begin{tabularx}{\textwidth}{L{3cm} L{4cm} Y}
\toprule
\textbf{Trang thai} & \textbf{Gia tri co the} & \textbf{Y nghia} \\
\midrule
$S_{\mathrm{parse}}$  & \texttt{parsed} / \texttt{parse-error}
  & Mo hinh co parse duoc thanh IR khong? \\
$S_{\mathrm{map}}$    & \texttt{verified} / \texttt{unresolved} / \texttt{unsupported}
  & Anh xa bien sang $\mathcal{Y}$ co chung nhan khong? \\
$S_{\mathrm{feas}}$   & \texttt{feasible} / \texttt{infeasible}
  & Mo hinh co nghiem kha thi khong? \\
$S_{\mathrm{bound}}$  & \texttt{bounded} / \texttt{domain-unbounded}
  & Mien nghiem co gioi han khong? \\
$S_{\mathrm{solve}}$  & \texttt{certified} / \texttt{timeout} / \texttt{numerical-failure}
  & Solver co chung nhan duoc ket qua khong? \\
\bottomrule
\end{tabularx}
\end{table}

\begin{table}[htbp]
\centering
\caption{Quy tac xu ly candidate theo tung trang thai.}
\small
\begin{tabularx}{\textwidth}{L{3.2cm} Y Y}
\toprule
\textbf{Trang thai} & \textbf{Duoc phep} & \textbf{Khong duoc phep} \\
\midrule
Parse error
  & Bao parser failure, giu raw output
  & Gan moi component la sai \\
Mapping unresolved
  & Bao structural metrics co dieu kien
  & Chay projected discrepancy \\
Infeasible
  & Bao IIS; $\Delta_{\to} = \mathrm{NA}$
  & Goi mien rong la unbounded \\
Domain-unbounded
  & Query trong safety box $B$
  & Dien giai witness trong $B$ la ket luan toan cuc \\
Timeout/failure
  & Giu witness duong neu da co; con lai inconclusive
  & Doi ``khong tim thay'' thanh ``tuong duong'' \\
\bottomrule
\end{tabularx}
\end{table}

%----------------------------------------------------------------------
\section{Mo-dun 1: Typed Canonical IR va Verified Projection}
%----------------------------------------------------------------------

\subsection{Muc dich}

Mo-dun 1 chuyen doi moi rang buoc ve mot \emph{dang chinh tac duy nhat}
(canonical form) de hai rang buoc toan hoc tuong duong se co bieu dien giong het nhau.

\subsection{6 buoc chuan hoa canonical}

\begin{enumerate}
  \item \textbf{Deterministic renaming:} doi ten bien theo provenance/requirement ID.
  \item \textbf{Chuan hoa sense:} chuyen ve $g(x) \leq 0$ hoac $h(x) = 0$;
        neu rang buoc la $\geq$, nhan ca hai ve voi $-1$.
  \item \textbf{Chuyen hang so:} dua tat ca hang so ve mot phia.
  \item \textbf{Chuan hoa $L_1$:} chia tat ca he so cho
        $s_c = \max\{1, \|a_c\|_1, |b_c|\}$ de triet tieu nhan tu ty le.
  \item \textbf{Sap xep bien:} sap xep bien theo thu tu tu dien A--Z.
  \item \textbf{Tao fingerprint:} sinh coefficient-support fingerprint.
\end{enumerate}

\begin{example}
\textbf{Chuan hoa $6x + 4y \leq 12$ va $3x + 2y \leq 6$:}

\textit{Rang buoc 1:} $6x + 4y \leq 12$, \quad $s_{c_1} = \max(1, 10, 12) = 12$
$\Rightarrow$ Sau chia: $0.5x + 0.333y \leq 1.0$

\textit{Rang buoc 2:} $3x + 2y \leq 6$, \quad $s_{c_2} = \max(1, 5, 6) = 6$
$\Rightarrow$ Sau chia: $0.5x + 0.333y \leq 1.0$

Ket qua: \textbf{Hai bieu dien canonical hoan toan giong nhau} $\Rightarrow$ khong con false positive.
\end{example}

%----------------------------------------------------------------------
\section{Mo-dun 2: Contextual Equivalence Matching}
%----------------------------------------------------------------------

\subsection{He thong nhan ghep cap}

\begin{table}[htbp]
\centering
\caption{6 nhan ghep cap theo thu tu bang chung giam dan.}
\small
\begin{tabularx}{\textwidth}{L{3.8cm} Y Y}
\toprule
\textbf{Nhan} & \textbf{Dieu kien gan} & \textbf{Vi du} \\
\midrule
\texttt{exact}
  & Canonical form giong het nhau
  & $3x+2y\leq6$ vs $3x+2y\leq6$ \\
\texttt{normalized}
  & Giong sau chuan hoa $L_1$
  & $6x+4y\leq12$ vs $3x+2y\leq6$ \\
\texttt{context-equivalent}
  & Solver xac nhan $\eta_{i\to j},\eta_{j\to i}\leq\tau$
  & Rang buoc LLM suy ra tu background \\
\texttt{group-equivalent}
  & Nhom nhieu rang buoc tuong duong (1-to-many)
  & LLM tach 1 rang buoc GT thanh 2 \\
\texttt{disproved-with-witness}
  & Solver tim counterexample $\eta > \tau$
  & $y=(3,4)$ thoa GT nhung vi pham LLM \\
\texttt{unresolved}
  & Solver timeout
  & Inconclusive \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Ham vi pham chuan hoa $v_c(y)$}

\begin{keyformula}
Voi rang buoc bat dang thuc $g_c(y) \leq 0$:
\[
v_c(y) = \frac{[g_c(y)]_+}{s_c + \varepsilon},
\qquad
s_c = \max\{1,\; \|a_c\|_1,\; |b_c|\},
\]
trong do $[z]_+ = \max(0, z)$ va $\varepsilon \approx 10^{-8}$.

Voi rang buoc dang thuc $h_c(y) = 0$:
\[
v_c(y) = \frac{|h_c(y)|}{s_c + \varepsilon}.
\]
\end{keyformula}

\begin{example}
\textbf{Tinh $v_c(y)$ tai $y = (3, 2)$ voi $c: 3x + 2y \leq 6$:}
\begin{align*}
g_c(y) &= 3(3) + 2(2) - 6 = 7 \quad \text{(vi pham)} \\
s_c &= \max(1, 3+2, 6) = 6 \\
v_c(y) &= \frac{7}{6} \approx 1.17
\end{align*}
Tai $y = (1, 1)$: $g_c = -1 \leq 0$ (thoa man) $\Rightarrow v_c = 0$.
\end{example}

\subsection{Hai cong thuc contextual implication scores}

\begin{keyformula}
Voi cap $(c_i^\star, \hat{c}_j)$, dat $H_{ij}$ la tat ca rang buoc da xac nhan dung (tru 2 cai dang xet):
\[
\eta_{i \to j} = \max_{y \in B \cap F(H_{ij}) \cap F(c_i^\star)} v_{\hat{c}_j}(y),
\qquad
\eta_{j \to i} = \max_{y \in B \cap F(H_{ij}) \cap F(\hat{c}_j)} v_{c_i^\star}(y).
\]
Gan \texttt{context-equivalent} khi va chi khi:
$\eta_{i \to j} \leq \tau$ \textbf{va} $\eta_{j \to i} \leq \tau$.
\end{keyformula}

\begin{example}
\textbf{Context-equivalent:} $c_{\mathrm{GT}}: x + y \leq 10$ vs $\hat{c}: 2x + 2y \leq 20$

Background: $x \geq 0, y \geq 0$.
\begin{itemize}
  \item $\eta_{i\to j}$: Tim $y$ thoa $x+y\leq10$ vi pham $2x+2y\leq20$.
    Khong co (vi $x+y\leq10 \Rightarrow 2x+2y\leq20$) $\Rightarrow \eta_{i\to j}=0$.
  \item $\eta_{j\to i}$: Tuong tu $\Rightarrow \eta_{j\to i}=0$.
\end{itemize}
Ca hai $=0\leq\tau$ $\Rightarrow$ \textbf{context-equivalent} \checkmark
\end{example}

\begin{example}
\textbf{Counterexample:} $c_{\mathrm{GT}}: x+y\leq8$ vs $\hat{c}: x+y\leq10$

$\eta_{j\to i}$: Tim $y$ thoa LLM ($x+y\leq10$) vi pham GT ($x+y\leq8$).
$y=(5,4)$: $9\leq10$ \checkmark nhung $9>8$
$\Rightarrow v_{c_\mathrm{GT}}(5,4)=\frac{1}{9}\approx0.11>\tau$

$\Rightarrow$ \textbf{disproved-with-witness}, counterexample: $(x,y)=(5,4)$.
\end{example}

%----------------------------------------------------------------------
\section{Mo-dun 3: Normalized Behavioral Discrepancy}
%----------------------------------------------------------------------

\begin{keyformula}
Voi matched pair $(c^\star, \hat{c})$ va $N$ diem test:

\textbf{Satisfaction disagreement rate:}
\[
D_{\mathrm{sat}}(c^\star, \hat{c}) =
\frac{1}{N}\sum_{i=1}^{N}
\mathbf{1}\!\left[\mathrm{sat}_{c^\star}(y^{(i)}) \neq \mathrm{sat}_{\hat{c}}(y^{(i)})\right]
\]

\textbf{Margin discrepancy (normalized RMSE):}
\[
D_{\mathrm{margin}}(c^\star, \hat{c}) =
\sqrt{\frac{1}{N}\sum_{i=1}^{N}
\left(v_{c^\star}(y^{(i)}) - v_{\hat{c}}(y^{(i)})\right)^2}
\]
\end{keyformula}

\begin{example}
\textbf{Tinh $D_{\mathrm{sat}}$ va $D_{\mathrm{margin}}$ voi 4 diem test:}

$c^\star: x+y\leq8$ vs $\hat{c}: x+y\leq10$, \quad $s_{c^\star}=8$, $s_{\hat{c}}=10$.

\begin{center}
\small
\begin{tabular}{ccccccc}
\toprule
$y^{(i)}$ & $x+y$ & $\mathrm{sat}^\star$ & $\mathrm{sat}^{\hat{}}$
  & $v_{c^\star}$ & $v_{\hat{c}}$ & $(v^\star-\hat{v})^2$ \\
\midrule
$(3,2)$ & 5  & T & T & 0     & 0    & 0      \\
$(4,4)$ & 8  & T & T & 0     & 0    & 0      \\
$(5,4)$ & 9  & F & T & 0.125 & 0    & 0.0156 \\
$(6,5)$ & 11 & F & F & 0.375 & 0.10 & 0.0756 \\
\bottomrule
\end{tabular}
\end{center}

\[
D_{\mathrm{sat}} = 1/4 = 0.25, \qquad
D_{\mathrm{margin}} = \sqrt{(0+0+0.0156+0.0756)/4} \approx 0.151
\]
\end{example}

\begin{warningbox}
$D_{\mathrm{sat}}$ va $D_{\mathrm{margin}}$ la \textbf{descriptive metrics} ---
chung mo ta sai lech, \textbf{khong chung minh} tuong duong hay khong tuong duong.
Bang chung tuong duong phai dung solver tu Mo-dun~2.
\end{warningbox}

%----------------------------------------------------------------------
\section{Mo-dun 4: Coverage-aware Directed Discrepancy}
%----------------------------------------------------------------------

\begin{keyformula}
\textbf{Under-constraining witness} (LLM qua long --- thieu rang buoc):
\[
\delta_{\to,i} = \max_{y \in \widehat{P}}\; v_{c_i^\star}(y),
\qquad
\Delta_{\to} = \max_{c_i^\star \in \mathcal{C}^\star}\; \delta_{\to,i}
\]

\textbf{Over-constraining witness} (LLM qua chat --- them rang buoc thua):
\[
\delta_{\leftarrow,j} = \max_{y \in P^\star}\; v_{\hat{c}_j}(y),
\qquad
\Delta_{\leftarrow} = \max_{\hat{c}_j \in \widehat{\mathcal{C}}}\; \delta_{\leftarrow,j}
\]
\end{keyformula}

\begin{example}
\textbf{Phat hien LLM bo sot rang buoc $x \leq 8$:}

GT: $x+y\leq10, x\leq8, y\leq8$. LLM: $x+y\leq10, y\leq8$ (bo $x\leq8$).

Solver tim trong $\widehat{P}$ vi pham $c^\star: x\leq8$:
\[
\max_{y\in\widehat{P}} \frac{[x-8]_+}{8} = \frac{[10-8]_+}{8} = \frac{2}{8} = 0.25
\]
Counterexample: $(10,0) \in \widehat{P}$, $v=0.25>\tau$
$\Rightarrow$ \textbf{LLM qua long}, $\Delta_{\to}=0.25$.
\end{example}

\begin{example}
\textbf{Phat hien LLM them rang buoc thua $x \leq 5$:}

GT: $x+y\leq10, x\leq8$. LLM: $x+y\leq10, x\leq5$ (qua chat).

Solver tim trong $P^\star = \{x+y\leq10,x\leq8\}$ vi pham $\hat{c}: x\leq5$:
\[
\max_{y\in P^\star} \frac{[x-5]_+}{5} = \frac{[8-5]_+}{5} = \frac{3}{5} = 0.6>\tau
\]
Counterexample: $(8,0)$ $\Rightarrow$ \textbf{LLM qua chat}, $\Delta_{\leftarrow}=0.6$.
\end{example}

\begin{table}[htbp]
\centering
\caption{Chan doan tu cap $(\Delta_{\to}, \Delta_{\leftarrow})$.}
\small
\begin{tabularx}{\textwidth}{C{2.2cm} C{2.5cm} Y}
\toprule
$\Delta_{\to}$ & $\Delta_{\leftarrow}$ & Chan doan \\
\midrule
$=0$ & $=0$ & Hai mien nghiem bang nhau trong tolerance $\tau$ \\
$>\tau$ & $=0$ & LLM thieu rang buoc --- mien LLM rong hon GT \\
$=0$ & $>\tau$ & LLM them rang buoc thua --- mien LLM hep hon GT \\
$>\tau$ & $>\tau$ & LLM vua thieu vua them sai --- mien khac han \\
NA & --- & LLM infeasible \\
\bottomrule
\end{tabularx}
\end{table}

\begin{warningbox}
Nguong $\tau$: so sanh $\delta$ voi mot nguong $\tau$ (thuong $10^{-6}$ den $10^{-3}$)
thay vi so sanh voi 0 chinh xac de tranh loi floating-point.
$\Delta=0$ chi duoc cong bo khi solver chung minh \textbf{global upper bound} $\leq\tau$.
Solver timeout khong co witness $\Rightarrow$ \texttt{inconclusive}.
\end{warningbox}

\begin{proposition}
Day la thay doi quan trong nhat so voi paper goc: rang buoc bi thieu
\textbf{khong con bi loai} khoi behavioral metric. Solver chu dong tim vung
feasible-set disagreement thay vi hy vong 100 random samples cham vao vung do.
\end{proposition}

%----------------------------------------------------------------------
\section{Mo-dun 5: Objective Discrepancy voi Ba Semantics}
%----------------------------------------------------------------------

\subsection{Tap diem chung $P_\cap = P^\star \cap \widehat{P}$}

Neu $P_\cap = \varnothing$ $\Rightarrow$ toan bo Mo-dun 5 tra ve \texttt{NA}.

\subsection{Cau hoi 1: Symbolic/Numerical Fidelity}

He so ham muc tieu co khop sau positive affine alignment khong?
Tim $a>0, b$ sao cho $\tilde{f}(y)=a\widehat{f}(y)+b \approx f^\star(y)$.

\subsection{Cau hoi 2: Value Fidelity}

\begin{keyformula}
\[
\Delta_{\mathrm{value}} = \max_{y \in P_\cap}
\frac{|f^\star(y) - \tilde{f}(y)|}{s_f + \varepsilon},
\qquad
s_f = \max\{1,\; \|a_f\|_1,\; |b_f|\}
\]
Tinh bang 2 linear/MILP solver queries (cho 2 dau cua $|\cdot|$).
\end{keyformula}

\begin{example}
$f^\star=3x+2y$ vs $\hat{f}=3x+3y$ (he so $y$ sai), $P_\cap: x,y\geq0, x+y\leq6$.

$s_f=\max(1,5,0)=5$. Tai $y=(0,6)$: $f^\star=12, \hat{f}=18$
$\Rightarrow |12-18|/5=1.2>\tau$ $\Rightarrow$ he so sai dang ke.
\end{example}

\subsection{Cau hoi 3: Decision Fidelity (Cross-Regret)}

\begin{keyformula}
$A^\star = \arg\min_{y \in P_\cap} f^\star(y)$, \quad
$\widehat{A} = \arg\min_{y \in P_\cap} \widehat{f}(y)$.

\textbf{Bidirectional worst-case cross-regret:}
\[
R_{\star \leftarrow \widehat{M}} = \max_{y \in \widehat{A}}
\frac{f^\star(y) - z^\star_\cap}{s_\star + \varepsilon},
\qquad
R_{\widehat{M} \leftarrow \star} = \max_{y \in A^\star}
\frac{\widehat{f}(y) - \widehat{z}_\cap}{s_{\hat{f}} + \varepsilon}
\]
Ca hai $=0$ $\Leftrightarrow$ hai optimizer sets trung nhau tren $P_\cap$.
\end{keyformula}

\begin{example}
$f^\star=3x+2y$ vs $\hat{f}=2x+3y$ tren mien $x+y=6,\; x,y\geq0$.

$A^\star=\{(0,6)\}$, $z^\star_\cap=12$; $\widehat{A}=\{(6,0)\}$, $\widehat{z}_\cap=12$.

$R_{\star\leftarrow\widehat{M}}$: dung nghiem LLM $(6,0)$ vao GT: $f^\star(6,0)=18$
$\Rightarrow (18-12)/5=1.2$.

$R_{\widehat{M}\leftarrow\star}$: dung nghiem GT $(0,6)$ vao LLM: $\hat{f}(0,6)=18$
$\Rightarrow (18-12)/5=1.2$.

Ca hai $=1.2>0$ $\Rightarrow$ \textbf{hai ben chon nghiem hoan toan trai nguoc nhau}.
\end{example}

\subsection{Symmetric Optimality Gap}

\begin{keyformula}
\[
\mathrm{Gap}_{\mathrm{sym}} = \frac{2|z^\star - \hat{z}|}{|z^\star| + |\hat{z}| + \varepsilon}
\]
\end{keyformula}

\begin{table}[htbp]
\centering
\caption{So sanh Symmetric Gap voi cong thuc goc.}
\small
\begin{tabularx}{\textwidth}{L{3cm} Y Y}
\toprule
& \textbf{Paper goc} $\frac{|z^\star-\hat{z}|}{|z^\star|}$
& \textbf{Symmetric Gap} $\frac{2|z^\star-\hat{z}|}{|z^\star|+|\hat{z}|+\varepsilon}$ \\
\midrule
Khi $z^\star=0$ & Chia cho 0 --- crash & Van tinh duoc \\
Khoang gia tri & $[0,\infty)$ & $[0,1]$ \\
Doi xung? & Khong & Co \\
\bottomrule
\end{tabularx}
\end{table}

%----------------------------------------------------------------------
\section{Output: Diagnostic Vector}
%----------------------------------------------------------------------

\[
\mathcal{E}(M^\star, \widehat{M}) = \bigl(
  S,\;
  \mathrm{ProjectionStatus},\;
  \mathrm{VarMatch},\;
  \mathrm{ConMatch},\;
  D_{\mathrm{sat}},\;
  D_{\mathrm{margin}},\;
  \Delta_{\to},\;
  \Delta_{\leftarrow},\;
  \Delta_{\mathrm{value}},\;
  R_{\star\leftarrow\widehat{M}},\;
  R_{\widehat{M}\leftarrow\star},\;
  \mathrm{Gap}_{\mathrm{abs}},\;
  \mathrm{Gap}_{\mathrm{sym}},\;
  \mathrm{WitnessCoverage}
\bigr)
\]

\begin{table}[htbp]
\centering
\caption{Y nghia tung thanh phan cua diagnostic vector.}
\small
\begin{tabularx}{\textwidth}{L{3.5cm} Y L{2.5cm}}
\toprule
\textbf{Thanh phan} & \textbf{Y nghia} & \textbf{Module} \\
\midrule
$S$ & State tuple (parse, map, feas, bound, solve) & M0 \\
ProjectionStatus & verified / unresolved / unsupported & M1 \\
VarMatch & Ti le bien anh xa thanh cong & M1 \\
ConMatch & Phan phoi nhan ghep cap & M2 \\
$D_{\mathrm{sat}}, D_{\mathrm{margin}}$ & Sai lech hanh vi tai diem test & M3 \\
$\Delta_{\to}, \Delta_{\leftarrow}$ & Under/over-constraining witness & M4 \\
$\Delta_{\mathrm{value}}$ & Sai lech gia tri ham muc tieu & M5 \\
$R_{\star\leftarrow\widehat{M}}, R_{\widehat{M}\leftarrow\star}$ & Cross-regret nghiem toi uu & M5 \\
$\mathrm{Gap}_{\mathrm{abs}}, \mathrm{Gap}_{\mathrm{sym}}$ & Optimality gap & M5 \\
WitnessCoverage & Ti le query co witness hop le & M2, M4 \\
\bottomrule
\end{tabularx}
\end{table}

\begin{warningbox}
Khong nen tao mot ``trust score'' tong hop duy nhat vi trong so se tuy y.
Toan bo vector phai duoc giu lai va cong bo.
\end{warningbox}

%----------------------------------------------------------------------
\section{Do phuc tap Solver-call}
%----------------------------------------------------------------------

Goi $m=|\mathcal{C}^\star|$, $n=|\widehat{\mathcal{C}}|$, $k$ la so canh sau blocking ($k\leq mn$):
\[
N_{\mathrm{solve}} \leq 2k + m + n + O(1), \qquad k \leq mn.
\]

\begin{itemize}
  \item $2k$: contextual implication (2 chieu moi canh ambiguous);
  \item $m+n$: directed queries ($m$ cho GT, $n$ cho LLM);
  \item $O(1)$: objective diagnostics.
\end{itemize}

%----------------------------------------------------------------------
\section{Ke hoach Thuc nghiem}
%----------------------------------------------------------------------

\subsection{Benchmark}

\begin{table}[htbp]
\centering
\caption{Cau truc benchmark 3 tap du lieu.}
\small
\begin{tabularx}{\textwidth}{L{3cm} C{1.5cm} C{2cm} Y Y}
\toprule
\textbf{Tap} & \textbf{Pilot} & \textbf{Full} & \textbf{Muc tieu} & \textbf{Nguon} \\
\midrule
Equivalent pairs & 100--150 & 400--600 & Kiem tra FPR & Certified transformations \\
Controlled mutants & 250--400 & 800--1200 & Detection/localization & OptArgus \\
Natural LLM outputs & 100--150 & 400--600 & External validity & Nhieu model, prompt \\
\bottomrule
\end{tabularx}
\end{table}

%----------------------------------------------------------------------
\section{Lo trinh Trien khai (12 tuan)}
%----------------------------------------------------------------------

\begin{description}[leftmargin=2em,labelsep=0.5em,style=nextline]
  \item[\textbf{Tuan 1--2.}] Semantic contract, state machine va typed IR.
  \item[\textbf{Tuan 3--4.}] Canonicalization, verified affine mapping.
  \item[\textbf{Tuan 5--6.}] Contextual implication, directed queries (HiGHS/SCIP).
  \item[\textbf{Tuan 7--8.}] Equivalent variants, mutants va gold annotation.
  \item[\textbf{Tuan 9.}] Natural LLM outputs (2--3 model families, 2 prompts, 3 seeds).
  \item[\textbf{Tuan 10.}] Baselines, ablations, cost profiling.
  \item[\textbf{Tuan 11.}] Robust statistics, expert audit.
  \item[\textbf{Tuan 12.}] Viet paper, artifact documentation.
\end{description}

\printbibliography[title={Tai lieu tham khao}]
\end{document}
"""

with open('/Users/tuyenkv/Documents/LLM4Opt/paper_brainstorm/equiceval_v2.tex', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done: equiceval_v2.tex written successfully")
