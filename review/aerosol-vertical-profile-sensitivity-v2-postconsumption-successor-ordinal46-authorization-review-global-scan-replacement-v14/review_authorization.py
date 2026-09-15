from __future__ import annotations
import base64
import hashlib
import zlib
from pathlib import Path

PAYLOAD_SHA256 = '76e7bc4c86462fa83973906d1f1617db466c773300295a6b8bb3bd0c984ca703'
PAYLOAD_B85 = r"""c-qB0YjfK;lHdI+IQc?yLuoAek%T^OmEy=dzD?|u>}2Xnqhe7cBylZ~3Q5WGxcuL*y8)2kOV-TJ-sM9~5kPmN(Qkm5CGkpg-
PtDFB+PZSaJ7z;O!J~B&b%y)qx9%VzDqOtxbV`&GMvhv|4QRXKF6tiN;lJW68kJI-aO@xS^U7F@OLJEhw;%2Nm+XtLY8!Vg`Y=9-
+L$SFT=qn&C&GP*~uC6&-~*cIQLH8y?gim^rXkmXXoc9!PH~k`+k2qd;k8uPNP14zWs=!j#=;I{KHw_^G*VGJbgDi_TRJP+4QV;{{BOc&EC!Y-
l>1~fseYo99@6C$8ibUhV1cYk0o&$FFRY7WTEdZJ20_XxMZD_MQNCY+c10TZ2O&coMt}oY_nP;?>gzm$N9%eCr*Me@|LIP9dDB@;w1c?xZB|fI`d^b1+b~_;
j8u1^Vy0;S!dfj`I&cdOXIrhCnWXM{Wu!jT>hexx?QLLAyQ5|{p0@m@rT|i$Ngn+eS?_K{otK{{O;`C`T2|iW6!7lyR-8i^ZUnV-pTAkuYWuXdb25vI(5H}U
`X%yq>n%3qCzhi()VWPr)M8NFc$Oz|BRiSz4!Vj{SRmCw0|<~vFUq)@NsZAbVtK09JunrD1XVtgH8SO({pd?eK_}m-
pRYOli=)Z>dpGoWB=^Tp8*cv=d=t*qgy0L-=1nf*VIdy79`;;(~o|+z9RuZBH{6NbbUGa>|TzBgZt~-8&1RBF9YZ}93f&9R0H$~gu-
>rZo)uZw#+b(Mz^;J2)lLHUILs<$NdS3nP|d4qDlK1Xz87FkP`jq+s!|3Zhu7<$J2i?KLcn-
M**8@UNSdkOK)!4M;iRgk|$dWp&RH|7uvSnFbdd?ccC6^=d*RDefO3dHcXN@v9*MO#z)#s95L!5eoGMJP<yNOCR#Yt=t=u8ZOI}-Hk%q-
0<&l|rwPO*j*P7!Nk9{JqMI(f{@J;KcA^`AM5e~p(m)n7_klg7&V90B@S6b>yev*q$Iva^(sWxlEzMgl<3~60BIn8joMx9rejEU6&F+Hjf^g2#f-
{dvm@yae7-&f>O%jB^<TBy2c|orP-
@B`aAWRIgK7t;$3)9SvALu9NW42lY5E}RxW(%Nd#Ryy%pMXz#7rN*G9R74UF&W!sm6_x6M48jC^1wt0zePGn7N=dIe+EFa2(6sw6qM8jt{RE=*vj&rG1al7r
UTqGOAK5=98mBO8m9Vh$JhZI8aSG=xsfKmrA076pxOZwz#DYuEOXO%llaVqZfGTxuGAC62ONnOreTz3UIbIwSxAZr0_cSxL8DESg)1(Uh7MLm8-
U_*pqc=xZ6a^$g-
dU`WP&$hvO7WKnk6YN)(m=qA2UGS1*vR{w1U3qoetaTC92p~ssR@f==rRt{(`N%?+7rCbh~HiKzO!EK^U(F*Pp@g+<p6e502&f=97z7@Ym7c>(}83BsP0mGu
_7jiGZ$4^5MFcz5>hZ&7l!j0o%ql7{%k`iA9*{pT1t8*4z3T95I{CK;gqJll*;5yfw@cu#}AUh|Mk&=4C9<ZBh?Q55g2A#a~q3tB8^~1L!Omv2?S{(%UtQ6a
c9of_Sj&XbV2N@;VD=p?}LA$N&`6Z$XiQ4gVGa{YlC$$qT8F&@?8)9rHI?9WVXTZPbSszAj_%Z9WUv*&Ue?eF6)`&CMD#O;LH$Znial)`cK+@ikbIwUlNaR=
8keUHBPBA%!@G5Eir$Mby$wHjy#b=V1n1?_BB@E}pd8riBi-0~P~_wRCi3`ouzA=hnmb))Z02n{2(w6cYlnx9D=ILlxBG1b(Mk03G2^60Sihe{wV#^0ey-gi
F7(2s>&Zvi<`A5Y9`ei1!H7$qD|s2yD<jd4W59${0*tQdKf3k_3#O4kCf<jEWu%0iXw1-
GFghL$ARGfb>Gk8$by<iQW$Q9nU&(w0zRRH0CbI{w=~0E;YN@Y?%BNr|0e|&Dd(V3p3*w8h(q=5AqI3`ta&%czJ*Q9sKm|x6vg!Y1i|!jkgp!h0ug!{0N#iq
(=}3Fm32CbM(Ttpv(v@EZG@_BqV}?SQ~!4T0<mYG|@r!&%k&9oSTl_(aZ6u3zkE91ki8f>Hs^tehe#Ma1PQ6^$uE^j3q17SIPVODj{&`YIrB03~k%>m#?>@`
ym=SkRlMr|AF2p%fF#k^#lw*UNf?tGXCLqj!#jSRuC+ki@_-
|auz2TIr}cSs>Dm4T>V7^Dhl_|mneV)s|X$cKbKwlh3?2`AzL@W2a(Z7>f70d{F1b3f;O3p;G%=MDmfrREIlPAOum864}ymXBb-FKAq=AmAIQ6)2SwWm?=mw
F$f&Wq#YnB<NE-
p%0B?)IfR(sFFv7snL<qSb#(&2l*#A59%DD*#YvSm7{u6itULTaRpe`*s*MaY>((FL=f>N`XAddvla=mpl@v;P!Et}w8#mUOcz;{qUYnBP2)p5jPNJO|CxEi
&d06sy{5RA$>DSp@b3tCYulkxGytWcY>RtR!^0fM!6U2%pV!{~NhV;eC)UQ>@j5GWJ(97X!NOE$~$DPL&QQezU%7g?PlK!~R>0{znT5XMmQA?M}+OWsc5KV^
nW{*jy5MrbXp_!fZ<0yEks3ksM3pI)7jy=MY@Bw6M8O$>@!=xL^T^{MWM@a=9hEkJbs_;^}&IsUD80ILt<w1Lp?H|r&5`e*QX^l-;AQ(--5Q|gQ-Ep~xHFj?
khp@_{YSXIA0+J~sS=zgQXNKBQY4RbQ2+`ukon;g;PMBbW$jobn63i|gBMJDip*sZ3~+{C=9)1N{=Q&<@|&o3oDK3H3%<aY=GiJO=fT8h0jYhwC<tiv39AK!
9qd1x{T+tzj2YYq0`3&tpw6K7iEQ}8;EKs{0)g5a!G-OKj8YTVLg=(9g=+zvGjTL<ShMhiD7%Q*+It;}m{WnAjekYo0}H65p4HS61PZ^CW*-
Mx@A82Oi|HF;rgxm4JR(U>!%%0(GPlWu#tZbL-grrX|MtJ@{F+F%N2o5;8F*oT-
&)fb@D(8CC`HE_@H|1^%5n3m%bz~3d<G+kK=)Og3~l_!NuF6H%^pxN*rhlo+FfNJCa60}W!1OglXe;Ff16T*ShX|VB!Ea+<t7-
WzzP9cdFT#$`j2#ylR(IFJn%kw2B^{jrymSDZHq(=m0Pw0gCB34VwI#nt4U=MUq0U5qM%U{zou4`gEMYMk-
^6P=#e_HSUUEPCJ#!D1Jgfl0}E5G!qE7d>q#(ETh;>4Zx@P~{^hCj?d7YZsU5$s=OHg{wt9S6<i(cYMb&=#|>cMgisuI4#*2Sm)EkfkVbf2h)w!u*GV6*Lvx
s+qNk8DN`R!<IbMj{+f{Ui8F!o3AtEdN$mt{K!g6pRu$#3CQ;AbcQR2Gip_6nHej{rg88@urcJKiSX$q_*|x<0+bT#RUB-
V%!PhNmM~@&X*IlpDC$D<7hW`H0hQUP;c)@Ex_n*mK=z{=V@WbnlnjJU#O_N7Qobf>8qT9auhVV@9+G8^x|=uV;!at6d)k^FnzrKV$i+gWB~;xo;LAsa0bES
@Gp_WQz@MKS63;q8g2%NnPSU{hq6Q&1DMFBbKG1^s;A|SpA)<>?&On^}En$PfM@`iLF|Z+bF>ARqz#!Afef6^FgR3WSVg3T^C%k2uB`73W5uqz1EZJ8~*rJ$
PR-AdH<rguSU=zOKZWdOlJgvM*iE>D5iZSTm_l{CR0~)I9vP!j?;zp98Z0FGa(|7_)x=9>-uc#1}%UX;$bZ-sX39bV@ct~E=r;1g1sFaK9cIQE@7%6*~*0>y
q<6NZS6=Tc`oEMTpKQH_^%ECw~G&RqP!se<JA(Xc8OSUyeU)YEtwE6dH#L2mYZK}Kcf8|pV{neQ@O_=wPi%mCSw8vvWY$1IbLa58M;Ho0cL>2;(s)D#Y7~v9
X4B|-
18g0g(i0~vks%X$G2uu>u)^Ye7IVLx9RVqrcExP9l^alwV*Q(OC%iDPR&kGUVFk>sM{x{+?&~ov)TPf9M+HsfRbLb^6%iW;ZLQU{c25z=&SwzT4&XYJU;sm}
Bvv?B)GO|L*5kf{TKYGgt8fKPEMny!Uk^_bD6awe|^C$41b-9ijT_|-d`zG*ZKyo7lt{Fv2tkr}YwXit_=7SH*f-
eY;)GieBYUs!npq%MGJQDV5QRq=c58Cn=CqcdR{_u#T?TIL$L$z|k5svxLiL;+hbv-L$hEOaz+0!KC9E)hTx$sEVJVVMHLH-<d@oyC4)-
dkOL8dKE9Ym(3qhn+6PSh-fvEuvkp+5lVx=lF5n|~5U-
R78IN)k`#F$#rgpxDuG3fXGsS@PTn)heKkVvAIwtPQwPA|!^hhIg%2=Ac`yFMdg1@*#Vb#xJLnLTh|VC7U(I-;*sC<JGJa;56t2QXEfHi|y7_J%B-
!RQi?l(X@=}D~oqED{%qaN~r{xt*I8<Rx%N`rBGF#JhN+*(mJEP!T`sSfez4aHn~-
4Ca}}E)3*WiSf_(mAV>>OpEM&t1L+)MESqrRfM&3`{hw<E=OX(|%HikAAzt5Abi@Z;fJw4s%YqS5pxZ=8{tiz?=r$dPD&FOkLkm1xjiEms<$yJ!!y;9*@SZk
hc`K(Ce&y84mP;&`VS^tp-FP+wuT?Y-BV{B^-mQ*?4mkj9FMyO48}*AT?vm~Bh^8AxFhdZ;C!<hS;NXf*cnOUy6`m-
<j~^%z6sJ?Wa~3fWXXetI)ClA59Rz*R{Q8!_(n$)Wxn7)y5nVhB1fhh4c6s~d%kbu&qLlpjAxB4NKccxUDXf}E-
o;BO|JL!GiF}8{#`f9q@#Lj+*e}O=j}QFR-`Y$0_5}hUUIQyant5p9Po67oRy1jxVK-eb!;E?wrq!b|g-
SZMNM17LppBt3F$VWBFcv@+g_wG{fWyqT3?tgVjT|Y#ZjGs;(Uv5%J00qWFX*Af%ciW86V<e7E{@$eh4-
oog<d{pigdz&!)b)hCHjQ)KZCw_es&M5it2Q;Sxq4-
2MNiSnXCs&)~yerc!CG5pj}EE)we;8Zj*dkrGApWm;6xR3f3d^8<nh45YRqCaI>R>lJ>5MNb{OY;|YQ*7>2&_6PuYY7up;PK27DI3vCe=YE36WQMl4<1(VCY
w!eVD#F}qB2%*X{N6rvi&A<2hwsI&C|KTyWrGt^aL5Y2>ZbWGQ&6?2x)gYqd;Chfv)reB*Dd8Z@y+<rkdBkFWfeIz!4^mWB-
=tQMX|6z#d4i;fv<1f4t<H+^RpPU}&`KPz5QN3>#2|?V37wFQvSif2^K%`wVG6ES0EnTY;JJVBh1M7#G%wTjtbu0-
6Z#eldo0Z+1yc?o@$FbSmtn+fM?{w3AjDw|hr=}|e{44Q$<x0xojTu9au%ea-
35@f1fysZxW)g$GK$_aJbQNlwiZs+J!aa#qqZ!YC%TP*@!u+)JC(vvu5gxD4hAA#ziL)KB@5nT6ZYAKgtm;N1Gj-
P=?ue0;{qL;Nx^(7ZJL!BDAGu<xq8BW@CqHDn@vL{+DO*q%yy&nhj=92f~?8o3`!V1vwcE%=nQS7(I%TByj{0Wea3V108tZ2o4R))L_p+~e3uJrv6jsUQ^q0
(57U?z0=MGX>5Y_3!`O{WdCkNsUWn9ULfg{_6Z10s+x3Fru#u+OJnJA#eGtw#fn36X@FNWP%83OisLj<&ta~^y8zYk9&;bF%5Ez-
nojN{^cVbrs1Z;b%zch0W!<F`EZzjSX-KJ73N^GqTVm4Px#HR*>Wd1cy`SErgwFyGV(@)5Z5Dx=mg09=doc7eO$N@>{IIm&YSmK+@!*>-<%}WROs&0R-
9;f4VmpLy{&XJv5z$b^0rBoYqF3m5EwxX0WG#wu)Hew<ksa9SKjU{{C5~DaYZk&&qT*zo-UJ4qkD!Jx11oxC?U0yfDTGp$U<Zz4I79X<lnpggkR^nv!vAOPe
U=4DAJ@NqJ+b1Avm(4Ta<!IsQWsvt)S)!7o$NA230T2fS4AU+{DOS`P&qy&R)>ycRO%(pvFj>LPV-HmIf-
4V>u^4lOpIGpet2+G>8a?3^e(YJ(TJ;zKodFcW$+6q~&-
h{DERIU?>ru^cKObh3a}$|^9+xz4@=^lb)(btD>K+!=c9_gz1c?db942ZOO#YFh&zH~S39I<J!A;j*M5YTD!180<l;%YzOH`Mvco|p`dn|UHu=OWL_OshQ9Z
1-0ld@D>ZI)R`wG=?=g^BoJfEQaT6_p3Z&;y9C|1Px9!S|hBzV-
88$LI>fztf&Hjp4Ohd;%9W27+xt_~a)CNZ&&q5(7?|fBu`X(sv*dpp!$k5#(E7#M}IpKx9wyy*^#<{woe8W%3)V2tQVJ7q}X)R0US0fMI_rpqf4J_MN!cHE$
Pjw_VyV0xyl#WIZq8BkWa6O?`!9lx-w+BerPc|0|X1wl$#-
s4+<mqj`NfUK192+XdQKl5xsJ_%M6(jNdH3;5Rwq)99a)m*1i{=Kh5Pvcmw2o!e6*i4_e9qYPj04{RbTF6lJqW8f3*?6gktJAGLl;`gp$_EefAnsf;iy#mt#
nhp^~q$BLSEl4~Zqkh0sYKPc+&H~p{`tY5Xc9IC)&wOAjarli#G3^EO0^N+0=ND6uyzub1u5%vH$9j8E;`sd-
XzxMA02W2XAisOxhlOg3Fzydxs>}s3?Ze{Zr=_^brIa!&^~iOi+awv5SX-N~tR<F{zVEce+6~}0odzH--
vKeU;HX8kj(`!i!U6tP_QSWbFgXi%_}OLtMd#FcmI8Y?IVegBJ-Yo&43adxaP;^(sS%c{L~+Ncs?`)!5O)kk!S;&2())h;g=HRe@p#C-Eq(s#11?Cc4E-
^QqxtvKk9_J^(0!>}OK&v|JZ)$1#OBqc>$;GUVX@0~`N~@QvHrKyW7D*9Aiu!88X(Yg_d-xzy@2+Suh4-
6A<Ha2P**9s!)2+#sE|TS2bs_^PVq~;Dmi@lzMozTjeZ4OvD%it<HY2*WL#45JNp6=<7ehQKt}aP7%nZp%u2-
<gnqn!%45T&H)Ts}wc(isF0!qhpvA7;04zQ}px8i1V`r8=O;81ESNl{z)m$57ZcGR##d*CvGHlcIh|N8eMyXYr=Obh=nfhA-*0KXP-Gs})kXwyz;Y#EyN2R>
f??T)5PMo%{w9$RxohDhb@iPaS$GWS$arsBDFs@(wfL{1_-
h+QV>L^1Iwipcy=v3~l;4Li|PmsUndyY<h?~xD1&@S3K4cjJpJ4R=vZ8FLopksN1(r*f#Z5k}g3C6;b^_qDSZ`NrkBe4hq4JaVfrnb+0LBkd?`FiDG3gj?;H
Bk3!fx3lIIZR4-
Oyz}G6eX46q;^4*V97m*p^XPjtQsaIVl+O04lT3^u;jP4<({!au1YJm?I~Cgi4zF5a!bb;Y<?I$==K84&1$XN{tNLBPhV4&f|D!L43)RoWnxus_88l}W4!Re
%x@!c5q|1Kcs&SirWh5FVzvO(S$R977=mZ!9ASoV9c|<WKFDt+>Nz7V;CNCnP%iQ~_oS2D^K1OTN44E~J)R9hP^k<f1U{Yz2|isWrGd71Q%KPk8sAvVI(T^x
EG1c28LCk302V?`B2*pfHz|=Eg*9{t@yWE5b*V3usbA41dcWvb^{Kj*hdqi!-
Em5JJ3su{ugSmT)O8~7+n{BWA`}+KnoI(5SXaB4d7(3X%kPUt4=CL~p5(QM-MBZYXWPoVJmFTiYYQwdsxk&`dN?D&z{{vQe3eKda%O`;r%OceEmzKG4(>$=1
WiFvlAx*|c<2iFSvjRLk!hXsy=Cew`up{xx+5H<`=<r&ApvhlX`C{rrRP7S!mOa_2~=d-
bCAl(aqqcaI<q&1NZ9~0bbxh&?2Rs_(s_lHqKP*bB8_)f;D{VOKRV_u1udNgTdrB6QnL*`Fl|A8y0}~nBJ_y50{Z)DCk2k;buTI~QSa4-
<HrG@tflITR7Oi(7U?9ES9q+a{6-!Is=cju&3z1_7RO$s$9E)M`JEPe`5v>rZdKl#>Sob-
H2nH`a5==2I_`JsTz*sP%%N2v@KMxL%INHkye;inn$Z{iP5ya?q#fl@N#Avuzqj`teH`Ub`DJiTeOpa7?M@aca8oft1Z#LNmvYaByM5=9G;sNI^IqVjz&hX^
SaA|CJXKO2*6X>9uKvO6oLt#Qj#BSu!VM4XWE2$SN8a-`3BYWfVi+wL-VqdNJl5MJFk`MKX~Wf0M2J(MG;$`&DLE2n(L^GE8Ux}K0Y5g`q7#JPJOaZP`W=7i
r77wXzr2rbB`O6ogcOWTU!Ke)6!@au`tYSw<^=xDOG0pt!jvit_go-
(5uxUDfkxURG}BG~RpkKs>#}d9Koy5pd@B!C7q9tN|6ms<k9d8h^IdJ@#_E`fP4pHXv8cWK^$^x?*jFr83E;HKSW`#?_7Q)k8u&H{iRcD8{Vf;?yoe2e3D|V
Kk+b*Wv9E)>JGyJ^>u5N*y#F@%?A{H(3~uhPFJ0irm*L&r;2%S1z5PDC0TVEE2REPGo55&w`>PAaYjBO%lkqSLY|~IKC!eLbRm(2&pHf=QD-
~kOBP?=z%X>P1C^zdZUF1DCF>vQvij8iI*Dw<yQ%W01m!)$bIn2!guWo!o>BUp4mw4e3v7)dTcNhX+#mP4s%Fnir<qqmDUtMJjbywPC$+uB)XMsOXik;M5u?
559{hj6Vd`U*%6G=4^!q2W2GNm+K<@n2+JSEoh?w7fKh!ek6!L0R@XK@>nF46Zk*9`TjZ;Q&5iCQPH%xEKq!r6Yzi*3Sl73YYH(v@z@cWUdUs1)WP8WM{#cH
i63EqLMrD@*|51f?i1Z|2S_O!Ev67V=5NDPZTlIqDtWKr5;_KMVb&Fp7JB+?lbJkf*`}FlTK{;2zo9S1TIKAXXg-
B;tCzZO*DIQKSTw%gdEz^onEsE{*sdSZ|>ag)ygtp}hUF<YRtCkM|YuD?_-ke|-
pU@zY+~PTBmU!Iibzz8li9)5rL>AQ<WV2P6nzVP3S<vbY*YtO4QmYQ?})W^DOHTpN1+Vnh|Ck31HU!y(eT^pYe*#$uRKg<qm90EY<1;)>tX_KEURFgsElYqU
Yqzk0gHLKE<YU#<8pRqiJA>xAEJ)}Se=+Kc@EAj!fRa>d)lQM`Kkn8aS7Ua(lP01r|87|B7`5HW!IZI)~h1S({?_{iB2TY5W{IL?-
)rb2zbpEk6YNTGNFRJ_GKRBB>*Owe2w`_uPSzH&QdiQ+$fQ{`WKKP5Ww+8vdSxS<jo%?tT$bRI9#`~1_p;(|jS9<9JqIO5jQ?P+HvZLE2Ln+LK1B2IC2;wCF
c&Nx6u%Fx&vwiGun;wNhxIt#9?LJ)PV&euPYaILk&tGiSxTY_Y#{MJpxDDIV{3vVGkzff-
G#7ocC=EXX}twg2FwyxI6N}n*)uVqw9md@*UwYG#z4e`>|?Pz#&cYRs8#kKto*QOg>K_dS%LjPA>$@<q_%6hSG751hzC)tx1SC{YK6jw863nxy&jBLXM1S7x
25mpXX==RF}I=KG@76vkGaY3po>M*)hy!paI9R6bi9w61G__ZGhJtMi7Nsm*NWdK<g<%`tAU5mBcmR09&Ui{$4ykM$7y6bpd?O@?fVovh9NNYe&al`ws2=3{
;B+~ekScxC)>2R3|lr%y(An%-Z*5jt&ZgRn_M5unTqZ*HKpLde)sm5dRG|Bf>;T3<Hly+C)b-
wjGscf^x<9r)<Qr&Bf$N7fv#LBzpq2$X;ahB_WUkLR|)?>AYyZho;Yfpq|z2Zr&SHinPW4iJeEL^Z2K%x@yw8!d;wGSA-8#cruMY;9^nd(Dndk<7t-
q?HEdSh?l4~09sXt=8Ph^~x8iLYLb>s0K+QM(_gU->O9P2~dKI+lhzWsBQ)i_3S9{ud~%tTF""".replace('\n', '')
raw = zlib.decompress(base64.b85decode(PAYLOAD_B85.encode('ascii')))
if hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA256:
    raise RuntimeError('V14 forensic payload SHA-256 drift')
exec(compile(raw, str(Path(__file__).resolve()), 'exec'), globals(), globals())
