content = r"""\documentclass[11pt,a4paper]{article}

% ── PACKAGES ──────────────────────────────────────────────────────────────────
\usepackage[margin=2.5cm]{geometry}
\usepackage{fontspec}
\setmainfont{Times New Roman}
\setmonofont[Scale=0.88]{Courier New}
\usepackage{polyglossia}
\setdefaultlanguage{vietnamese}
\usepackage{microtype}
\usepackage{mathtools,amssymb,amsmath,amsthm}
\usepackage{booktabs,tabularx,array}
\usepackage{enumitem}
\usepackage{xspace}
\usepackage[most]{tcolorbox}
\usepackage{graphicx}
\usepackage{csquotes}
\DeclareQuoteAlias{american}{vietnamese}
\usepackage[
  backend=biber, style=authoryear-comp, language=english,
  maxcitenames=2, maxbibnames=99,
  uniquelist=false, uniquename=init, giveninits=true,
  doi=true, url=true, isbn=false
]{biblatex}
\DeclareLanguageMapping{vietnamese}{english}
\addbibresource{equiceval_improvement.bib}
\usepackage[unicode,colorlinks=false,pdfborder={0 0 0}]{hyperref}

% ── THEOREM ENVIRONMENTS ──────────────────────────────────────────────────────
\theoremstyle{plain}
\newtheorem{theorem}{Dinh ly}[section]
\newtheorem{lemma}[theorem]{Bo de}
\newtheorem{proposition}[theorem]{Menh de}

\theoremstyle{definition}
\newtheorem{definition}[theorem]{Dinh nghia}
\newtheorem{example}[theorem]{Vi du}

\theoremstyle{remark}
\newtheorem{remark}[theorem]{Nhan xet}
\newtheorem{warningthm}[theorem]{Luu y}

% ── SIMPLE BOX FOR KEY FORMULAS ───────────────────────────────────────────────
\newtcolorbox{keybox}{
  enhanced, breakable,
  colback=white, colframe=black, boxrule=0.6pt,
  arc=0pt, left=4pt, right=4pt, top=3pt, bottom=3pt
}

% ── LAYOUT ────────────────────────────────────────────────────────────────────
\setlength{\parindent}{1.5em}
\setlength{\parskip}{0.3em}
\setlength{\emergencystretch}{3em}
\renewcommand{\arraystretch}{1.18}
\setlist[itemize]{leftmargin=1.6em,itemsep=0.25em,topsep=0.25em}
\setlist[enumerate]{leftmargin=1.8em,itemsep=0.3em,topsep=0.25em}
\setcounter{tocdepth}{2}

% ── COLUMN TYPES ──────────────────────────────────────────────────────────────
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}

% ── MACROS ────────────────────────────────────────────────────────────────────
\newcommand{\method}{\textsf{EquiCEval}\xspace}
\newcommand{\GT}{M^{\star}}
\newcommand{\LLM}{\widehat{M}}
\newcommand{\Pgt}{P^{\star}}
\newcommand{\Pllm}{\widehat{P}}

% ── TITLE ─────────────────────────────────────────────────────────────────────
\title{
  \textbf{EquiCEval: Danh gia thanh phan tuong duong\\
  cho mo hinh toi uu hoa do LLM sinh ra}\\[0.5em]
  \normalsize\textit{Tai lieu ky thuat --- Phuong phap, Cong thuc va Vi du so hoc}
}
\author{Kieu Van Tuyen}
\date{Thang 8 nam 2026}

% ══════════════════════════════════════════════════════════════════════════════
\begin{document}
\maketitle
\begin{abstract}
Tai lieu nay mo ta chi tiet framework \method, mot he thong danh gia tham chieu
(reference-based evaluation) cho mo hinh LP/MILP do LLM sinh ra. \method khac phuc
ba diem yeu cua Refai va Ahmed: (1)~false penalties tren cac bieu dien tuong duong,
(2)~bo sot rang buoc bi thieu trong Cons-RMSE, va (3)~bat on dinh thong ke.
Framework gom 6 mo-dun lien tiep: pre-check, typed canonical IR, contextual
equivalence matching, normalized behavioral discrepancy, coverage-aware directed
discrepancy, va objective discrepancy. Moi mo-dun duoc trinh bay kem vi du so hoc
cu the de lam ro nguyen tac hoat dong.
\end{abstract}

\tableofcontents
\newpage

% ══════════════════════════════════════════════════════════════════════════════
\section{Dong luc va Van de}
% ══════════════════════════════════════════════════════════════════════════════

\subsection{Ba diem yeu cua Cons-RMSE}

Khi dung LLM de sinh mo hinh toi uu hoa, ta can danh gia do chinh xac cua mo hinh
sinh ra (candidate) so voi mo hinh chuan (reference). Paper goc cua Refai va Ahmed
su dung Cons-RMSE---do lech binh phuong trung binh tren cac rang buoc---nhung
co ba diem yeu cot loi.

\begin{definition}[Ba diem yeu cua Cons-RMSE]
\begin{enumerate}
  \item \textbf{Reference-form bias}: hai rang buoc tuong duong toan hoc bi phat khac
        nhau chi vi viet theo dang khac.
  \item \textbf{Coverage blind spot}: rang buoc bi thieu (omission) bi loai khoi
        phan tu so; 100 random samples thung khong cham vao vung sai khac nho gan bien.
  \item \textbf{Statistical fragility}: Pearson $r=0.9229$ giam con $0.1792$ khi bo
        mot outlier; Spearman $\rho\approx0.3946$ tren toan bo du lieu.
\end{enumerate}
\end{definition}

\begin{example}[Reference-form bias]
Cho hai rang buoc:
\[
  c_1:\; 6x + 4y \leq 12 \qquad c_2:\; 3x + 2y \leq 6.
\]
$c_1$ va $c_2$ xac dinh cung mien nghiem (tai moi $(x,y)$, $c_1$ thoa man khi
va chi khi $c_2$ thoa man). Tuy nhien, neu dung so sanh he so truc tiep:
\[
  \mathrm{Cons\text{-}RMSE}(c_1,c_2)
  = \sqrt{(6-3)^2+(4-2)^2+(12-6)^2}
  = \sqrt{9+4+36} = 7 \neq 0.
\]
Day la false positive: mo hinh LLM viet dung nhung bi tinh la sai.
\end{example}

\subsection{Muc tieu cua \method}

\method tra loi bon cau hoi chinh:

\begin{enumerate}
  \item Khong gian quyet dinh cua hai mo hinh co tuong thich khong?
  \item Mien nghiem kha thi khac nhau o dau?
  \item Ham muc tieu khac nhau ve dang so hoc hay ve quyet dinh xep hang?
  \item Thanh phan nao gay sai khac va co bao nhien chung cu (witness) chung minh?
\end{enumerate}

% ══════════════════════════════════════════════════════════════════════════════
\section{Ky hieu va Bai toan}
% ══════════════════════════════════════════════════════════════════════════════

\begin{definition}[Mo hinh toi uu hoa]
Mot mo hinh toi uu hoa la bo tu $(X, D, f, \mathcal{C})$ trong do:
$X$ la tap bien quyet dinh; $D$ la mien (binary $\{0,1\}$, integer hoac continuous);
$f:X\to\mathbb{R}$ la ham muc tieu; $\mathcal{C}$ la tap rang buoc.
\end{definition}

Ta ky hieu Ground Truth la $\GT=(X^\star,D^\star,f^\star,\mathcal{C}^\star)$
va mo hinh LLM la $\LLM=(\widehat{X},\widehat{D},\widehat{f},\widehat{\mathcal{C}})$.

\begin{definition}[Khong gian quyet dinh chung $\mathcal{Y}$]
Vi hai mo hinh co the dung ten bien khac nhau, ta khai bao khong gian quyet dinh ngu nghia
chung $\mathcal{Y}$ voi hai anh xa:
\[
  \pi^\star : X^\star \to \mathcal{Y}, \qquad
  \widehat{\pi} : \widehat{X} \to \mathcal{Y}.
\]
Cac tap nghiem kha thi duoc so sanh trong mien an toan $B\subseteq\mathcal{Y}$:
\[
  \Pgt = B \cap \{\pi^\star(x) : x \in F(\GT)\}, \qquad
  \Pllm = B \cap \{\widehat{\pi}(\hat{x}) : \hat{x} \in F(\LLM)\}.
\]
\end{definition}

\begin{warningthm}
\method la reference-based framework: no kiem tra quan he giua hai mo hinh trong
mien va tolerance da khai bao, nhung khong chung minh GT phan anh dung toan bo y
dinh nguoi dung. Truong hop khong co verified projection hoac solver khong dong duoc
bound phai bao la \textbf{inconclusive}, khong duoc doi thanh ``dung''.
\end{warningthm}

% ══════════════════════════════════════════════════════════════════════════════
\section{Mo-dun 0: Pre-check va State Machine}
% ══════════════════════════════════════════════════════════════════════════════

Truoc khi chay bat ky metric nao, \method gan mot tuple trang thai:
\[
  S = (S_{\mathrm{parse}},\; S_{\mathrm{map}},\; S_{\mathrm{feas}},\;
       S_{\mathrm{bound}},\; S_{\mathrm{solve}}).
\]

\begin{table}[htbp]
\centering
\caption{Cac trang thai trong evaluator state machine.}
\label{tab:states}
\small
\begin{tabularx}{\textwidth}{L{3cm} L{5cm} Y}
\toprule
\textbf{Trang thai} & \textbf{Gia tri} & \textbf{Y nghia} \\
\midrule
$S_{\mathrm{parse}}$
  & \texttt{parsed} / \texttt{parse-error}
  & Mo hinh co parse duoc thanh IR? \\
$S_{\mathrm{map}}$
  & \texttt{verified} / \texttt{unresolved} / \texttt{unsupported}
  & Anh xa bien sang $\mathcal{Y}$ co chung nhan? \\
$S_{\mathrm{feas}}$
  & \texttt{feasible} / \texttt{infeasible}
  & Mo hinh co nghiem kha thi? \\
$S_{\mathrm{bound}}$
  & \texttt{bounded} / \texttt{domain-unbounded}
  & Mien nghiem co gioi han? \\
$S_{\mathrm{solve}}$
  & \texttt{certified} / \texttt{timeout} / \texttt{numerical-failure}
  & Solver co chung nhan duoc ket qua? \\
\bottomrule
\end{tabularx}
\end{table}

\begin{table}[htbp]
\centering
\caption{Quy tac xu ly candidate theo tung trang thai.}
\label{tab:handling}
\small
\begin{tabularx}{\textwidth}{L{3.3cm} Y Y}
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
  & Bao IIS; $\Delta_{\to}=\mathrm{NA}$
  & Goi mien rong la unbounded \\
Domain-unbounded
  & Query trong safety box $B$
  & Dien giai witness trong $B$ la ket luan toan cuc \\
Timeout / failure
  & Giu witness duong neu da co; con lai \texttt{inconclusive}
  & Doi ``khong tim thay'' thanh ``tuong duong'' \\
\bottomrule
\end{tabularx}
\end{table}

% ══════════════════════════════════════════════════════════════════════════════
\section{Mo-dun 1: Typed Canonical IR va Verified Projection}
% ══════════════════════════════════════════════════════════════════════════════

\subsection{Muc dich}

Mo-dun 1 chuyen moi rang buoc ve dang chinh tac duy nhat (canonical form):
hai rang buoc tuong duong toan hoc se co bieu dien giong het nhau sau chuyen doi.

\subsection{Cau truc Intermediate Representation}

Moi bien luu: \texttt{domain} (binary/integer/continuous), \texttt{lb}, \texttt{ub},
\texttt{unit}, \texttt{provenance}.
Moi rang buoc tuyen tinh $c$ luu: coefficient map $\{v\mapsto a_v\}$, right-hand side
$b_c$, va sense ($\leq$ hoac $=$).

\subsection{6 buoc chuan hoa}

\begin{enumerate}
  \item \textbf{Deterministic renaming}: doi ten bien theo provenance / requirement ID.
  \item \textbf{Chuan hoa sense}: chuyen ve $g(x)\leq0$ hoac $h(x)=0$;
        neu $\geq$ thi nhan hai ve voi $-1$.
  \item \textbf{Chuyen hang so}: dua hang so ve cung mot phia.
  \item \textbf{Chuan hoa $L_1$}: chia tat ca he so cho
        $s_c = \max\{1,\|a_c\|_1,|b_c|\}$ de triet tieu nhan tu ty le duong.
  \item \textbf{Sap xep bien}: theo thu tu tu dien.
  \item \textbf{Tao fingerprint}: coefficient-support fingerprint de de xuat index permutations.
\end{enumerate}

\begin{example}[Chuan hoa $L_1$]
\label{ex:canonicalize}
Xet hai rang buoc $c_1: 6x+4y\leq12$ va $c_2: 3x+2y\leq6$.

\medskip
\textit{Buoc 4 cho $c_1$}: $s_{c_1}=\max(1,\;6+4,\;12)=12$.
Chia: $(6/12)x+(4/12)y\leq12/12 \;\Rightarrow\; 0.5x+0.333y\leq1$.

\textit{Buoc 4 cho $c_2$}: $s_{c_2}=\max(1,\;3+2,\;6)=6$.
Chia: $(3/6)x+(2/6)y\leq6/6 \;\Rightarrow\; 0.5x+0.333y\leq1$.

Sau chuan hoa, hai canonical form \textbf{giong het nhau}
$\;\Rightarrow$ khong con false positive.
\end{example}

\subsection{Thu tu uu tien anh xa bien}

\begin{enumerate}
  \item Exact name match.
  \item Name alias (vi du \texttt{x\_1\_1}$\,\to\,$\texttt{x11}).
  \item Normalized name (strip underscores/spaces, case-insensitive).
  \item Requirement ID.
  \item Semantic role.
  \item Fingerprint (he so, bounds, vi tri trong objective).
\end{enumerate}

% ══════════════════════════════════════════════════════════════════════════════
\section{Mo-dun 2: Contextual Equivalence Matching}
% ══════════════════════════════════════════════════════════════════════════════

\subsection{He thong nhan}

Sau khi chuan hoa, Mo-dun 2 xay dung bieu do 2 phia giua $\mathcal{C}^\star$ va
$\widehat{\mathcal{C}}$ roi ghep cap theo thu tu bang chung:

\begin{table}[htbp]
\centering
\caption{6 nhan ghep cap, thu tu bang chung giam dan.}
\label{tab:labels}
\small
\begin{tabularx}{\textwidth}{L{4cm} Y}
\toprule
\textbf{Nhan} & \textbf{Dieu kien} \\
\midrule
\texttt{exact}
  & Canonical form giong het nhau. \\
\texttt{normalized}
  & Giong sau chuan hoa $L_1$ (Vi du~\ref{ex:canonicalize}). \\
\texttt{context-equivalent}
  & Solver chung nhan $\eta_{i\to j}\leq\tau$ va $\eta_{j\to i}\leq\tau$. \\
\texttt{group-equivalent}
  & Mot nhom rang buoc tuong duong voi nhom khac (1-to-many). \\
\texttt{disproved-with-witness}
  & Solver tim counterexample $y^\star$ voi $\eta>\tau$. \\
\texttt{unresolved}
  & Solver timeout, khong ket luan duoc. \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Ham vi pham chuan hoa}

\begin{definition}[Normalized violation $v_c(y)$]
\label{def:violation}
Cho rang buoc bat dang thuc $g_c(y)\leq0$:
\begin{equation}
  \label{eq:violation-ineq}
  v_c(y) = \frac{[g_c(y)]_+}{s_c + \varepsilon}, \qquad
  s_c = \max\{1,\;\|a_c\|_1,\;|b_c|\},
\end{equation}
trong do $[z]_+=\max(0,z)$ va $\varepsilon\approx10^{-8}$ tranh chia cho 0.
Cho rang buoc dang thuc $h_c(y)=0$:
\begin{equation}
  \label{eq:violation-eq}
  v_c(y) = \frac{|h_c(y)|}{s_c + \varepsilon}.
\end{equation}
\end{definition}

Viec chia $s_c$ dam bao $v_{c_1}(y)=v_{c_2}(y)$ khi $c_1,c_2$ tuong duong
(nhan boi duong): neu khong chia, hai rang buoc phuong trinh $6x+4y\leq12$
va $3x+2y\leq6$ cho RMSE khac nhau du cung xac dinh mien nghiem.

\begin{example}[Tinh $v_c(y)$]
Voi $c: 3x+2y\leq6$ (nen $a_c=(3,2)$, $b_c=6$, $s_c=\max(1,5,6)=6$).

\begin{itemize}
  \item Tai $y=(3,2)$: $g_c(y)=3(3)+2(2)-6=7>0$ (vi pham).
    $v_c(y)=7/6\approx1.17$.
  \item Tai $y=(1,1)$: $g_c(y)=3+2-6=-1\leq0$ (thoa man).
    $v_c(y)=0$.
\end{itemize}
\end{example}

\subsection{Contextual implication scores}

\begin{definition}[Contextual implication]
\label{def:implication}
Cho cap $(c_i^\star,\hat{c}_j)$. Dat $H_{ij}$ la tap tat ca rang buoc da duoc
chung nhan dung (tru $c_i^\star$ va $\hat{c}_j$). Hai scores:
\begin{equation}
  \label{eq:eta}
  \eta_{i\to j} = \max_{y\in B\cap F(H_{ij})\cap F(c_i^\star)} v_{\hat{c}_j}(y),
  \qquad
  \eta_{j\to i} = \max_{y\in B\cap F(H_{ij})\cap F(\hat{c}_j)} v_{c_i^\star}(y).
\end{equation}
Gan nhan \texttt{context-equivalent} khi $\eta_{i\to j}\leq\tau$
\textbf{va} $\eta_{j\to i}\leq\tau$.
\end{definition}

\begin{example}[Context-equivalent]
\label{ex:ctx-equiv}
Bai toan san xuat: $x\geq0$, $y\geq0$ (background $H_{ij}$).
So sanh $c_\mathrm{GT}: x+y\leq10$ voi $\hat{c}: 2x+2y\leq20$.

\begin{itemize}
  \item $\eta_{i\to j}$: tim $y$ thoa $x+y\leq10$ vi pham $2x+2y\leq20$.
    Khong co (vi $x+y\leq10\Rightarrow2x+2y\leq20$) $\Rightarrow\eta_{i\to j}=0$.
  \item $\eta_{j\to i}$: tuong tu $\Rightarrow\eta_{j\to i}=0$.
\end{itemize}
Ca hai $\leq\tau$ $\Rightarrow$ \texttt{context-equivalent}.
\end{example}

\begin{example}[Disproved-with-witness]
\label{ex:counterex}
So sanh $c_\mathrm{GT}: x+y\leq8$ voi $\hat{c}: x+y\leq10$.

\begin{itemize}
  \item $\eta_{i\to j}$: tim $y$ thoa GT vi pham LLM. Khong co
    (vi $x+y\leq8\Rightarrow x+y\leq10$) $\Rightarrow\eta_{i\to j}=0$.
  \item $\eta_{j\to i}$: tim $y$ thoa LLM ($x+y\leq10$) vi pham GT ($x+y\leq8$).
    Tai $y=(5,4)$: $5+4=9\leq10$\checkmark, nhung $9>8$ nen
    $v_{c_\mathrm{GT}}(5,4)=(9-8)/9\approx0.11>\tau$.
\end{itemize}
Counterexample: $(x,y)=(5,4)$ $\Rightarrow$ \texttt{disproved-with-witness}.
\end{example}

% ══════════════════════════════════════════════════════════════════════════════
\section{Mo-dun 3: Normalized Behavioral Discrepancy}
% ══════════════════════════════════════════════════════════════════════════════

\subsection{Muc dich}

Voi cac cap da ghep tu Mo-dun 2, Mo-dun 3 do muc do sai lech hanh vi tai tap diem test.
Thay vi random samples, \method dung ba loai diem co chu dich:
\textit{feasible interior}, \textit{boundary}, va \textit{parameter-perturbed}.

\subsection{Cong thuc}

\begin{definition}[$D_{\mathrm{sat}}$ va $D_{\mathrm{margin}}$]
\label{def:dsat-dmargin}
Cho matched pair $(c^\star,\hat{c})$ va $N$ diem test $\{y^{(i)}\}$:

\begin{equation}
  \label{eq:dsat}
  D_{\mathrm{sat}}(c^\star,\hat{c}) =
  \frac{1}{N}\sum_{i=1}^{N}
  \mathbf{1}\!\left[
    \operatorname{sat}_{c^\star}(y^{(i)})\neq\operatorname{sat}_{\hat{c}}(y^{(i)})
  \right],
\end{equation}

\begin{equation}
  \label{eq:dmargin}
  D_{\mathrm{margin}}(c^\star,\hat{c}) =
  \sqrt{\frac{1}{N}\sum_{i=1}^{N}
  \bigl(v_{c^\star}(y^{(i)})-v_{\hat{c}}(y^{(i)})\bigr)^2}.
\end{equation}
\end{definition}

\begin{table}[htbp]
\centering
\caption{So sanh $D_{\mathrm{sat}}$ va $D_{\mathrm{margin}}$.}
\label{tab:dmetrics}
\small
\begin{tabularx}{\textwidth}{L{2.2cm} Y Y}
\toprule
 & $D_{\mathrm{sat}}$ & $D_{\mathrm{margin}}$ \\
\midrule
Do cai gi & Ti le bat dong thoa/vi pham & RMSE chuan hoa muc vi pham \\
Khoang & $[0,1]$ & $[0,\infty)$ \\
Phat hien tot & LLM bo sot rang buoc & LLM sai he so nho (bien dich chuyen) \\
$=0$ nghia la & GT va LLM luon dong thuan & Violation giong het nhau \\
\bottomrule
\end{tabularx}
\end{table}

\begin{example}[Tinh $D_{\mathrm{sat}}$ va $D_{\mathrm{margin}}$]
\label{ex:dmetrics}
So sanh $c^\star: x+y\leq8$ voi $\hat{c}: x+y\leq10$.
$s_{c^\star}=\max(1,2,8)=8$; $s_{\hat{c}}=\max(1,2,10)=10$.

\begin{center}
\small
\begin{tabular}{@{}lrcccccc@{}}
\toprule
$y^{(i)}$ & $x+y$ & $\mathrm{sat}^\star$ & $\mathrm{sat}^{\hat{}}$
  & $v_{c^\star}$ & $v_{\hat{c}}$ & Bat dong? & $(v^\star-\hat{v})^2$ \\
\midrule
$(3,2)$ & 5  & T & T & 0 & 0 & -- & 0 \\
$(4,4)$ & 8  & T & T & 0 & 0 & -- & 0 \\
$(5,4)$ & 9  & F & T & $1/8=0.125$ & 0 & \textbf{Yes} & 0.0156 \\
$(6,5)$ & 11 & F & F & $3/8=0.375$ & $1/10=0.10$ & -- & 0.0756 \\
\bottomrule
\end{tabular}
\end{center}

\[
D_{\mathrm{sat}} = \tfrac{1}{4},
\qquad
D_{\mathrm{margin}} = \sqrt{\tfrac{0+0+0.0156+0.0756}{4}}
= \sqrt{0.0228} \approx 0.151.
\]
\end{example}

\begin{warningthm}
$D_{\mathrm{sat}}$ va $D_{\mathrm{margin}}$ la \textbf{descriptive metrics}---chung
mo ta sai lech nhung khong chung minh tuong duong hay khong tuong duong.
Bang chung tuong duong phai den tu solver (Mo-dun~2).
\end{warningthm}

% ══════════════════════════════════════════════════════════════════════════════
\section{Mo-dun 4: Coverage-aware Directed Discrepancy}
% ══════════════════════════════════════════════════════════════════════════════

\subsection{Han che cua random sampling}

Neu LLM bo sot mot rang buoc quan trong, vung sai khac giua $\Pgt$ va $\Pllm$
co the rat hep---100 random samples thuong khong cham vao do, dan den
$D_{\mathrm{sat}}\approx0$ du mo hinh thuc su sai.
Mo-dun 4 su dung solver de \emph{chu dong} tim vung do.

\subsection{Hai huong tim kiem}

\begin{definition}[Under- va over-constraining witnesses]
\label{def:delta}
\textit{Under-constraining witness} (LLM qua long, thieu rang buoc):
\begin{equation}
  \label{eq:under}
  \delta_{\to,i} = \max_{y\in\Pllm}\,v_{c_i^\star}(y),
  \qquad
  \Delta_{\to} = \max_{c_i^\star\in\mathcal{C}^\star}\,\delta_{\to,i}.
\end{equation}

\textit{Over-constraining witness} (LLM qua chat, them rang buoc thua):
\begin{equation}
  \label{eq:over}
  \delta_{\leftarrow,j} = \max_{y\in\Pgt}\,v_{\hat{c}_j}(y),
  \qquad
  \Delta_{\leftarrow} = \max_{\hat{c}_j\in\widehat{\mathcal{C}}}\,\delta_{\leftarrow,j}.
\end{equation}
\end{definition}

Bang~\ref{tab:diagnosis} tom tat ket luan tu cap $(\Delta_{\to},\Delta_{\leftarrow})$.

\begin{table}[htbp]
\centering
\caption{Chan doan tu cap $(\Delta_{\to},\Delta_{\leftarrow})$.}
\label{tab:diagnosis}
\small
\begin{tabularx}{\textwidth}{C{2.5cm} C{2.8cm} Y}
\toprule
$\Delta_{\to}$ & $\Delta_{\leftarrow}$ & Chan doan \\
\midrule
$\leq\tau$ & $\leq\tau$ & Hai mien nghiem bang nhau trong tolerance $\tau$. \\
$>\tau$    & $\leq\tau$ & LLM thieu rang buoc; $\Pllm\supset\Pgt$. \\
$\leq\tau$ & $>\tau$    & LLM them rang buoc thua; $\Pllm\subset\Pgt$. \\
$>\tau$    & $>\tau$    & Hai mien khac han nhau. \\
NA         & ---         & LLM infeasible. \\
\bottomrule
\end{tabularx}
\end{table}

\begin{example}[Under-constraining: bo sot $x\leq8$]
\label{ex:under}
GT: $x+y\leq10,\;x\leq8,\;y\leq8$.
LLM: $x+y\leq10,\;y\leq8$ (thieu $x\leq8$).

Solver giai~\eqref{eq:under} cho rang buoc $c^\star: x\leq8$:
\[
  \max_{y\in\Pllm}\,\frac{[x-8]_+}{\max(1,1,8)}
  = \frac{[10-8]_+}{8} = \frac{2}{8} = 0.25.
\]
Counterexample: $(x,y)=(10,0)\in\Pllm$, $v=0.25>\tau$
$\Rightarrow$ $\Delta_{\to}=0.25$ (LLM qua long).
\end{example}

\begin{example}[Over-constraining: them $x\leq5$]
\label{ex:over}
GT: $x+y\leq10,\;x\leq8$. LLM: $x+y\leq10,\;x\leq5$.

Solver giai~\eqref{eq:over} cho rang buoc $\hat{c}: x\leq5$:
\[
  \max_{y\in\Pgt}\,\frac{[x-5]_+}{\max(1,1,5)}
  = \frac{[8-5]_+}{5} = \frac{3}{5} = 0.6.
\]
Counterexample: $(8,0)\in\Pgt$, $v=0.6>\tau$
$\Rightarrow$ $\Delta_{\leftarrow}=0.6$ (LLM qua chat).
\end{example}

\subsection{Ngu nghia certificate}

\begin{itemize}
  \item Mot feasible incumbent voi violation $>\tau$ da la \textbf{witness sound},
        du solver chua chung minh optimality.
  \item $\Delta_{\to}=0$ hoac $\Delta_{\leftarrow}=0$ chi duoc cong bo khi solver
        chung minh \textbf{global upper bound} $\leq\tau$ cho moi query.
  \item Solver timeout khong co witness $\Rightarrow$ \texttt{inconclusive};
        khong duoc doi thanh ``tuong duong''.
\end{itemize}

\begin{proposition}
Day la thay doi quan trong nhat so voi paper goc: rang buoc bi thieu
\textbf{khong con bi loai} khoi behavioral metric. Solver chu dong tim vung
feasible-set disagreement thay vi phu thuoc vao 100 random samples.
\end{proposition}

% ══════════════════════════════════════════════════════════════════════════════
\section{Mo-dun 5: Objective Discrepancy voi Ba Semantics}
% ══════════════════════════════════════════════════════════════════════════════

\subsection{Muc dich va ba cau hoi}

Paper goc dung mot chi so duy nhat (Obj-RMSE) dan den: (1) loi chia cho $|z^\star|$
khi $z^\star=0$; (2) khong phan biet ba dang sai khac. Mo-dun 5 tach thanh:

\begin{enumerate}
  \item \textbf{Symbolic fidelity}: he so co khop sau positive affine alignment?
  \item \textbf{Value fidelity}: hai ham lech bao nhieu tren mien chung?
  \item \textbf{Decision fidelity}: optimizer sets co trung nhau?
\end{enumerate}

Dat $P_\cap=\Pgt\cap\Pllm$. Neu $P_\cap=\varnothing$ thi Mo-dun 5 tra ve \texttt{NA}.

\subsection{Symbolic fidelity}

Tim $a>0$, $b$ sao cho $\tilde{f}(y)=a\widehat{f}(y)+b\approx f^\star(y)$.
$a,b$ phai duoc suy ra tu quan he he so, \textbf{khong} duoc fit tren du lieu.

\subsection{Value fidelity}

\begin{definition}[Value fidelity $\Delta_{\mathrm{value}}$]
\begin{equation}
  \label{eq:value}
  \Delta_{\mathrm{value}} = \max_{y\in P_\cap}
  \frac{|f^\star(y)-\tilde{f}(y)|}{s_f+\varepsilon},
  \qquad s_f = \max\{1,\;\|a_{f^\star}\|_1,\;|b_{f^\star}|\}.
\end{equation}
Tinh bang 2 solver queries cho 2 dau cua $|\cdot|$.
\end{definition}

\begin{example}[Value fidelity]
$f^\star=3x+2y$ vs $\hat{f}=3x+3y$ (he so $y$ sai),
$P_\cap=\{x,y\geq0,\;x+y\leq6\}$.

$s_f=\max(1,3+2,0)=5$. Tai $y=(0,6)$: $f^\star=12$, $\hat{f}=18$.
\[
  \Delta_{\mathrm{value}} \geq \frac{|12-18|}{5} = 1.2 > \tau.
\]
He so sai dang ke.
\end{example}

\subsection{Decision fidelity}

\begin{definition}[Bidirectional cross-regret]
\label{def:regret}
Dat $A^\star=\arg\min_{y\in P_\cap}f^\star(y)$ va
$\widehat{A}=\arg\min_{y\in P_\cap}\widehat{f}(y)$.

\begin{equation}
  \label{eq:regret}
  R_{\star\leftarrow\LLM} = \max_{y\in\widehat{A}}
  \frac{f^\star(y)-z^\star_\cap}{s_\star+\varepsilon},
  \qquad
  R_{\LLM\leftarrow\star} = \max_{y\in A^\star}
  \frac{\widehat{f}(y)-\widehat{z}_\cap}{s_{\hat{f}}+\varepsilon}.
\end{equation}
Ca hai $=0$ $\Leftrightarrow$ $A^\star=\widehat{A}$ tren $P_\cap$.
\end{definition}

\begin{example}[Cross-regret]
$f^\star=3x+2y$ vs $\hat{f}=2x+3y$ tren $P_\cap=\{x+y=6,\;x,y\geq0\}$.

$A^\star=\{(0,6)\}$, $z^\star_\cap=12$;
$\widehat{A}=\{(6,0)\}$, $\widehat{z}_\cap=12$.

\[
  R_{\star\leftarrow\LLM}: f^\star(6,0)=18 \Rightarrow (18-12)/5=1.2,\qquad
  R_{\LLM\leftarrow\star}: \hat{f}(0,6)=18 \Rightarrow (18-12)/5=1.2.
\]
Ca hai $=1.2>0$ $\Rightarrow$ hai ben chon nghiem hoan toan trai nguoc nhau.
\end{example}

\subsection{Symmetric optimality gap}

\begin{definition}[Symmetric optimality gap]
\label{def:gap}
\begin{equation}
  \label{eq:gap-sym}
  \mathrm{Gap}_{\mathrm{sym}} =
  \frac{2|z^\star-\hat{z}|}{|z^\star|+|\hat{z}|+\varepsilon}.
\end{equation}
\end{definition}

\begin{table}[htbp]
\centering
\caption{So sanh $\mathrm{Gap}_{\mathrm{sym}}$ voi cong thuc goc.}
\label{tab:gap}
\small
\begin{tabularx}{\textwidth}{L{3cm} Y Y}
\toprule
 & \textbf{Paper goc} $\dfrac{|z^\star-\hat{z}|}{|z^\star|}$
 & \textbf{Symmetric Gap} (cong thuc~\ref{eq:gap-sym}) \\
\midrule
Khi $z^\star=0$ & Chia cho 0 (crash) & Van tinh duoc \\
Khoang gia tri & $[0,+\infty)$ & $[0,1]$ \\
Doi xung? & Khong & Co \\
\bottomrule
\end{tabularx}
\end{table}

% ══════════════════════════════════════════════════════════════════════════════
\section{Diagnostic Vector}
% ══════════════════════════════════════════════════════════════════════════════

Thay vi mot diem so duy nhat, \method tra ve vector chan doan:
\begin{equation}
  \label{eq:vector}
  \begin{aligned}
  \mathcal{E}(\GT,\LLM) = \bigl(
    &S,\;
    \mathrm{ProjectionStatus},\;
    \mathrm{VarMatch},\;
    \mathrm{ConMatch},\;
    D_{\mathrm{sat}},\;
    D_{\mathrm{margin}},\;\\
    &\Delta_{\to},\;
    \Delta_{\leftarrow},\;
    \Delta_{\mathrm{value}},\;
    R_{\star\leftarrow\LLM},\;
    R_{\LLM\leftarrow\star},\;
    \mathrm{Gap}_{\mathrm{abs}},\;
    \mathrm{Gap}_{\mathrm{sym}},\;
    \mathrm{WitnessCoverage}
  \bigr).
  \end{aligned}
\end{equation}

\begin{table}[htbp]
\centering
\caption{Y nghia tung thanh phan cua vector~\eqref{eq:vector}.}
\label{tab:vector}
\small
\begin{tabularx}{\textwidth}{L{3.8cm} Y L{2cm}}
\toprule
\textbf{Thanh phan} & \textbf{Y nghia} & \textbf{Module} \\
\midrule
$S$ & State tuple (parse, map, feas, bound, solve) & M0 \\
ProjectionStatus & verified / unresolved / unsupported & M1 \\
VarMatch & Ti le bien anh xa thanh cong & M1 \\
ConMatch & Phan phoi nhan ghep cap & M2 \\
$D_{\mathrm{sat}},\;D_{\mathrm{margin}}$ & Sai lech hanh vi tai diem test & M3 \\
$\Delta_{\to},\;\Delta_{\leftarrow}$ & Under/over-constraining witness & M4 \\
$\Delta_{\mathrm{value}}$ & Sai lech gia tri ham muc tieu & M5 \\
$R_{\star\leftarrow\LLM},\;R_{\LLM\leftarrow\star}$ & Cross-regret nghiem toi uu & M5 \\
$\mathrm{Gap}_{\mathrm{abs}},\;\mathrm{Gap}_{\mathrm{sym}}$ & Optimality gap & M5 \\
WitnessCoverage & Ti le query co witness hop le & M2, M4 \\
\bottomrule
\end{tabularx}
\end{table}

\begin{warningthm}
Khong nen tao mot ``trust score'' tong hop vi trong so se tuy y.
Toan bo vector phai duoc giu lai va cong bo.
\end{warningthm}

% ══════════════════════════════════════════════════════════════════════════════
\section{Do phuc tap Solver-call}
% ══════════════════════════════════════════════════════════════════════════════

Goi $m=|\mathcal{C}^\star|$, $n=|\widehat{\mathcal{C}}|$,
$k$ la so canh sau blocking ($k\leq mn$).
Budget tong so solver calls:
\begin{equation}
  N_{\mathrm{solve}} \leq 2k + m + n + O(1).
\end{equation}

\begin{itemize}
  \item $2k$: contextual implication (2 chieu moi canh ambiguous).
  \item $m+n$: directed queries ($m$ cho GT, $n$ cho LLM).
  \item $O(1)$: objective diagnostics.
\end{itemize}

Day la bound ve so lan goi; moi MILP query van NP-hard. Phai tach
\textit{early witness mode} (dung ngay khi co violation $>\tau$) khoi
\textit{full certification mode} (dong global bound; timeout $\to$ inconclusive).

% ══════════════════════════════════════════════════════════════════════════════
\section{Cau hoi Nghien cuu va Gia thuyet}
% ══════════════════════════════════════════════════════════════════════════════

\begin{description}[leftmargin=2em,labelsep=0.5em,style=nextline]
  \item[\textbf{RQ1.}] \method co giam false-positive rate tren cac formulation
    tuong duong so voi exact component matching?
    \textit{H1}: Canonical IR + contextual implication giam dang ke false penalties.

  \item[\textbf{RQ2.}] Directed queries co phat hien va dinh vi omission, sign,
    coefficient, domain va index errors tot hon 100 random samples?
    \textit{H2}: $\Delta_{\to}$ va $\Delta_{\leftarrow}$ tang mutation recall, dac biet
    voi loi chi bieu hien gan feasible boundary.

  \item[\textbf{RQ3.}] Metric nao con lien he on dinh voi expert labels sau rank
    correlation, clustered bootstrap va leave-one-family-out?
    \textit{H3}: Diagnostic vector on dinh hon raw Cons-RMSE;
    khong scalar metric nao du thay the semantic labels.

  \item[\textbf{RQ4.}] Ket luan ve model/prompt co thay doi khi dung equivalence-aware
    evaluation?
    \textit{H4}: Mot phan ranking cua paper goc thay doi vi equivalent formulations
    khong con bi tinh la loi.

  \item[\textbf{RQ5.}] Directed queries ton them bao nhieu solver calls va o error
    regime nao muc tang recall bu duoc chi phi?
    \textit{H5}: Blocking giam manh $k/(mn)$; early witness mode dat recall/time
    tot hon perturbation tren omissions va thin-margin mutations.
\end{description}

% ══════════════════════════════════════════════════════════════════════════════
\section{Ke hoach Thuc nghiem}
% ══════════════════════════════════════════════════════════════════════════════

\subsection{Benchmark}

\begin{table}[htbp]
\centering
\caption{Cau truc benchmark ba tap du lieu.}
\label{tab:benchmark}
\small
\begin{tabularx}{\textwidth}{L{3.2cm} C{1.8cm} C{2cm} Y}
\toprule
\textbf{Tap} & \textbf{Pilot} & \textbf{Full} & \textbf{Muc tieu} \\
\midrule
Equivalent pairs  & 100--150 & 400--600   & Kiem tra false-positive rate \\
Controlled mutants & 250--400 & 800--1200  & Detection va localization \\
Natural LLM outputs & 100--150 & 400--600  & External validity \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Baselines}

\begin{enumerate}
  \item Paper goc Refai--Ahmed: component P/R + 100-sample Cons-RMSE.
  \item Token / exact symbolic matching.
  \item Canonical matching, khong contextual implication.
  \item EquivaMap (competitor truc tiep).
  \item ReLoop-style random/parameter perturbation.
  \item \method day du.
\end{enumerate}

\subsection{Yeu cau thong ke bat buoc}

Bao Spearman va Kendall (khong chi Pearson); clustered bootstrap theo problem family;
leave-one-family-out; confidence intervals; parse-error/unsupported/inconclusive
phai la outcome rieng, khong impute.

% ══════════════════════════════════════════════════════════════════════════════
\section{Lo trinh 12 tuan}
% ══════════════════════════════════════════════════════════════════════════════

\begin{description}[leftmargin=2.5em,labelsep=0.5em,style=nextline]
  \item[\textbf{Tuan 1--2.}] Semantic contract, state machine, typed IR; tai tao metric paper goc.
  \item[\textbf{Tuan 3--4.}] Canonicalization, verified affine mapping, exact/normalized matching.
  \item[\textbf{Tuan 5--6.}] Contextual implication, directed queries, timeout policy (HiGHS/SCIP).
  \item[\textbf{Tuan 7--8.}] Equivalent variants, mutants, gold annotation pilot.
  \item[\textbf{Tuan 9.}] Natural LLM outputs (2--3 model families, 2 prompts, 3 seeds).
  \item[\textbf{Tuan 10.}] Baselines, ablations, cost profiling.
  \item[\textbf{Tuan 11.}] Robust statistics, expert audit.
  \item[\textbf{Tuan 12.}] Viet paper, artifact documentation.
\end{description}

\printbibliography[title={Tai lieu tham khao}]
\end{document}
"""

with open('/Users/tuyenkv/Documents/LLM4Opt/paper_brainstorm/equiceval_v3.tex', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
