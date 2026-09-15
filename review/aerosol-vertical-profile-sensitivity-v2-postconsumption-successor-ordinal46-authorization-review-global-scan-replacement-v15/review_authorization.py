from __future__ import annotations
import base64
import hashlib
import zlib
from pathlib import Path

PAYLOAD_SHA256 = '7440e1e039182f53a8ae2e25f15e6b8e466c7b355be998cfc37acfefeabcdc48'
PAYLOAD_B85 = r"""c-rkeYg60Evfud?I((6R)^?1+khs=cMTj|}DhZS!*{bVMDp?wV7FqJq!-3`S-%oeXjAr!mgY4eAA1+_8rJkOio_<e{y*OGJmgQw>7BkB-
{KYbgQ^O9!D78~R3X{D(`7BB0M<-
f7$<Oz8av%6}`Sp(^3gzc0k)M)mzKkP>CF;pjvghICOFPB!a^@@ey0`c3U|@ZmoPIFIhUwTxN3QMl4~Ij0?(`4)u05E$9y|7qk4{+MW$$de|F%CgY1H-
E^y2EqdjIM2Jq|u}-
p)_FL+14dwmWnO?vca#@0>yZ@ECBN92^Z!*vZiD>w|Gz%vL`8@y2Fxlte*y#p2X=?4S#)@ce*v6BZ_Z>aYCtsk<6<mr;^Bz^rVsM5c9<%)!M*aW{%xKeU6R<
F1{h_fhQsNo?)%3A%SdGzYYaW8<S`U^{HV!nC_O7`)*iR$*Lk`Glknt@qQ@FJ~WhQdi65Zz5&b9rOps{dWgPeD42CY#Od-
)92HRFG%RI<DS5N4^NJdJ=S;L!tS38j}I6~!q7hS-
W?43o_pZUVbqazHH9Gu{lfu%kzxo?Fl1nZ)D7RgW6V8pogq6MzO@I3gLgxAG&r0eu=!iU@c#6AVofLKIB;S6Aw4{sPEKzwF2B%QeB%w-
+&Mlvw&(V{W7|DAJQ*Ik!{OZa2J^l%96BCM<~Tsq-p9!lhoE+}KwW{imeuaX47k2xt@hq@^6g^syEVPM#C<{N-
qMbNMagV%OR_CqX@CO4cw?9#Zr!<^Fqmo2Wu9T#@!iT=*+IryUSQvij3kZQM)x=TZ~Vvj5`}EEXTV<?Kk*Ov=Z7wPgh@cTdx)V&4+uk>fY_tMmZ|X#5l`Yci
q+Vdfe8u;Gd=S?f$kUM!1!%!1T1VxyzS;;;=6>L<v4ET(m;ly5T(>g?(NpnehMPn9T~3gq;iEE{XBA?U@^}RBV%QFQEWVP;Da9;Voc9Z*&=DRk<<s{AEXWr^
Ox!My*(Hnn=hOo`v)LFv)FS%?voax?HC~RsrA5~lJQNPG5F44H|#WulX1)Jm>t6$neC1N`h$kqP8{DKpW8vg+C3IJk;__UmU`W{W?NsjFvh)vC}_dl?cP0mb
p1P)q#!1O1wUdS-
9nlym~!DeEwsWT60eR?Wr^BugcEYpTRgaa+!A6YmcbtVB(<Uk`pQX57fWCO4gBG!_f}{x7|qwiPp~y+4?xTuxW}nW*<;$$*e0mzkW_@}cu?kH8&Q1^O=KD{$
Pe$v1r|j~PneDt%+eu>a*ixnoFL_3P=Gu3624oW?FYd876|Rgcn{h!A?XG4Qep~Qp}xQ(b+s|OUA7WagMffP6>w$Q6)2>3b0DEEtF4&~V^|6}01@c3AianDG
bITerbnYeY-
{O=v#@?G@WN~xpaf>0BeYYH{$*MZEnXH!h#f?g%BMCH=bkO>Z^(Wibz~fLw097KWC=Vp&rdHtfjzzc`Uze8#g`8j8u#C)r&m{#si_S~pOy>;;6L2AcF!Vtvn
&l}0WQbBLoiTvg3?|t@6im7&?G8Jh+>O*9&^BxF)N9(*kSsl+yk-rBePu?TISrnU_)U@7G5B%AEqtAbFw4ibI(seXMIpvgMrS=#~K33VU9xE3__!QFQd|4>F
9LtIc45i%<PmQg=BOzNY_t5bDaBT2yp%>@QS%pmSjPiTrOEy3kXIHRFz$XtLUK_AoV@px#aP|X%IwC!?X$b<gX#@P@J$c3Nq@!&|}7vN9JVdI;!X~ye5^Sw=
cRB&q~Jr7L}mZwQvQkvAJ9yb9<ZHBG@cz4gn7#0TVtl=1(b0iq5HO@DEyZ6Necl7($e6^qA-Ya*u%)a&CU_BS4dD2!P5M7J#<D6~d?y2L8Pd(iPzI8DQ@i(f
kkC<=a9u5M}A81_U&oGmpF|1NTSTfxh%le@WBy(2jQu`baMm%|HqJ=_h^&HUT!LMM#h^+-
Z1}l8RM<IIa$bFA5+2K^&U;VaD`Hw6S7baSA(hD=>0~7OfbRu>*la6m+-
^Le{j~rKy2Svz#{Mj)q9zT!53?vO2PoC37s~PtxKhh+L$K%mOg$Gr3o{GCE@n@Z(c(Aqmq*w#ANQA-MYDU>GvH%{L6^#I3^DKkVS4g;>|_4vy$3x!J&Y*G_H
Jo{H$vo(jpqKQ0#-U$V4?qlBci+HIW}dIOr(GFQT_w2d)DXR9NVc92K-
upog?JflEAe_EuOxYR>u5W1W+eV^#9QlOAok>>%8>oy7mMeLD)MV|LL(^JU31Nh$0w*ZkMZ5qB_vIK_Viv$FnA!Q;CQlxW4zwqE0K^33Gta42RSy+?+$P<D&
7*4R5Vri9?b%@3=8gUhHqCh~>16nuyFR!?fTY22Xu^PWZ5+L{h-
$Xhf#_5ra?SqS(W*}h;o?x_0h!h0h49Guyba1FyKm~w@5C_yPdnRV;LgE0{QY}aF17sbNUDQkVxFm09VFFdZ<GIx)^~H5J>a$unERf!|F|{~YyGD-
|>BZ5XECf+D05v4Xu5aIkka7DCK5$?WFvf6W-
viQ~75*2&0n+m^r%{UHR=Nq)nvx3`Cxc5gQCe~EsH~Z@3g|5^u$&(k^{;7Pmoe*7JPXl2F1&=AFV<|Avqg>H^a{*YoKh6qEak#Cak&s*lvw23#!<<9RohqOm
-c-|fV6b;+1xC_jl1ebAW>+4`OKJNkq0)!mdO-^<P~LqY<T;XJ%E7sxx580kV@?f-
B{Xw%rJD<moO4@{=$_+P4P>0rIf~xZj}}cs%jvosp`OB3nf_3rT{)0wg)W9g@h^|ifX|ql+i)0$R`8Pijv$DG<P;-
mbTZ6^_mrwrC2c*92!Q$6r~%O<Us^mFkg~|(oEqJEz$zCQ}L$IVFEC(4jpK4F?8@kv;(t{#}U;aq7-
z6JZL!2LI+p)fq6XU3VEpjojB%IK5(5`w9nQYXb6~js~B4wvUp)B3RxGl;6m!+Nfn%mz|anY6584ThaLi~Fs@pl*Gvt<_dH+(pXv*&pGeA|_k35>oc?W+YXn
`PmylI}&-m3CY)e@bx?-
b2jzxNFCF~9>tVIi$<CltHngvvg<Zfq72ep`hA*~AeCWLLIv)ruX2E&XMFq9Y*m3}S6{t{7f)lE=c_YoSIQI8NS$>v%R9b?SAO&IriWw;)wMyz&-
LAe#+%I`!AQCZv&n~;4#!?(_66ihR{-
8wwE2RjkPbUZ+ts0gcxOgL&8ncz39ZQ(;1nE(y=T{vVUg1!QCED?!rG_`9e^0`k%OkFHFNH<FHcF_$s2jY8rO<X4yqRL{8`&XlnO2EJTrsDN&V%s&V5NQJ<)
gz%O;5-7VXcAr|=WGS)F_s!rDHREnz{uGIql*^45yd2-wY($?gCsD71{9!+uOMiJ@4Wz|4ibOU_zpC+Z)K1n&vgKk(tdCMnd5)K@CwwrA-
5ZS5BF;ZQSpWQibAB0)fL>x9AU+OH{%1F+iJ!+ZiuCTNNuwW2McI;#zng}_c`OmKGn~SJb&FX(R$Sn#I=-
7A+Dhj8QQM0rK3fYIqMkS_x<N*Wa}*7quZAkqhPzg@3)`1q`h#OH0=`72t;cVQ4T{*v-
d~jOC^!YR5e|BNV!>$KsbSb73<QOVOf=uEMCD&h(&A|@<Y&~>icq{9@(<i{_8|;e}_0%6QyEAtDCVra@0)htB6LXY)xGVQVkS3S&YXPT@;LMscML0%XzjXDn
HHPEPN3`p(yC6$Mxl{H97g{m9;8>RK=*uX0NY2Rx6f#9Wnx-Zv~$5_j$o4kp&7RC^94y#-
^Tos+#+^Rx2=5BSc+k`nD=kG;TmrpPc>GxmlwD7bT{W9p8o&u${71VT($ZY?*i?w2L$o_-{Xeaq`175_O=imPpo7nCsiWGhtI_`Q-
Z>Jng<ZE_tn?>u9d%?{}x#bS61b{VZ;S)zd)t{}yLi_LUV^DX3Q_3snzImfXBTkxdUxxn1Y=r=ni&6sqTrSBTIZ<lme+BIg+=_(%L=u5rZm=Cn!5l^@o3So6
mB_7cfLTWH5r1d*xFJVw*!--Q@9{G|>eFDBI2M7BH;IVIxSGG(WN06z&#>h`FTvgarL`be1+RlSKkWK=~26iLwv;JYM?)Av(zo9alf_E2nHouv8rZQbsBc+_
hERfgJ0m67RH&3e~Zo_~#(jF}UG=7Esf4t9SGDhK^7l9)7G28<tSy6SlCo>4o4>Tc}CS*S9XnR(}@XsNnqCh?#p8?o9Q>Kf>h6d?p2KAE@5(x60*)zLGrAT6
m$Gs@CsR(W~PoQJV?l%1<0(%9o`$3tKgG0HXRd6K$-uE(=6?i5Am<pvKf&l(N}(k2iEc&;LSw>AOT2KAlAv9cA&acsmf_{`L#_Qp`Xm|6>!1ck-eU}5n{yv3
2wsrR^gaGvvk0L0?72GO0@NO<J>@QYlAct1u`doHW?XMxZzP^v-DAjlaT`}n_w7R?VBiN)mnd~$Yk@oi#VUw)mQO}M~dCm#w6f@41zZ-j(}YaiSDdj-
><TYYWHZ6kMW&2qevYlK0>gNomS{OAD=2x|=b6UBLDM73J!RKP+o(m9`A{?Fu#Rkvy(2j$10A_s!gPP9ZuKbx`*QuOgiPRWKJJkqeRDVA$B>9-
7jGd}<^v_ywqVJq^b)bpRF7ymdxp!q9)GJ?;zo8Pd=Vpo`EI5{qEE~Q=N&o=KIY&s;cI6~MogVrpJskX0bJ4Gi`!93<9;A-
+y1Y{WX#_eJq3#d>(w=uTTA!Cg{ime39eNtquwK}ojOH9!o2v!ML*0^HWVTb_hF&rF_JZ7mq2N5d57Iy~=)d<uoO_T3W4p79hMUdl%_Y9kYT-
@)>0rta20n;Kh+5vVX8d+$sY@hI(g<PvdjgXu+srg_hHP=|F_--K9n(TbeARuBEMuW)H;*xXmrFLR|3>O04EWOu`<GN0OUR|DI@fO9x+Vn|Yv7merZ>Z(UKs
@#350gjjiZ+XLe@r<r75lf<KDC!X``mY3AjZuWizj&Fr#_IxTk9}TEtRqwTM5LTR^S_|`^D4Kt@8ic1J|-
><v`o+1s?zb0d`lo8wJcPuCPhC<oll%ui`|nTvW4=$sJZ^cC6}b(kq&!yB;RRgN1tyW?Ml|Cs&_N&nBNIUvAK$AawE3P&#65()_c+BW5aL7Z?>5JX%qR6#1L
Ev|z{}%GP|WF8k>dMC=}UF*kFtd>RQJYHC<!1}dH+01pSt3@AYS1X+HF3KXzZBgfm9mqwmtS?0yu=dOCES-JnkRJK?Nm9>e54}zK(Vz#qKJ4|0^elUwt28y>
s6gXn;U_EkL)|w9mwY4p$h-D|gL_?Y^M@|73{hu%$+BCZ@W=o$G&to$1r5Z++(Fh3h&(uw@+ie=eh!)3=V_)C*LahuE8$iwzG~VZ*xqe#g+2_s{^iVXs%bc-
O19I&^YMK7aPv1kja(!<f2zV_Gs~a|vOTH$V6HV5m@&y;}BFi^o3XRPgc2vb{SwH=Z1-MaOd94z0bQR-
!Y!<C~DVKiKu<|1;bxxVbVdQ<V8n`o2w^W^2<zlBcXmvCxR#NFE6<(2OJRwoSQ)tl#+E55Dm6m;zGWt7;=oJb%;GJPntQAK;+Efd}qc1dJT8MV5;{`?Hh_7P
y3B>7@_=`STpMhlfl~^_P)lo(@*scND8M*V(Cab1lDjJZSA{~)#LdwfJ<C^(C#uOXiK@n$tol<3sxqMyoOJmGEkE6vWphgIFu{Kl~Cd|TT?t3nQZBcmlo?C!
(JGF!AaB#_jvMEDb0b2{sVMUiGN}%H2(PV|j#bF;{4>6a1l0v>_=;~yG{_^HWr0p(l!@ppGYsQhAyC`_MuSxC2j+))M&X%AGNj*IIiPJdsJ*3NijKXN~^gfP
kx8XiZ7Cwa0k5CSoJTiXI^%T5q?F3TDaEVhE*pIbfsLkskgh_7%deJj{%^i|$&yQGTV;xwM1xsx_vTCin3kZHl-
h`yII?NVx7UyScSJUm&wj(_A;NuGpQ50AU)8I2xKk1_*iV_fAW-
T2DQUOvsx8Y=NEOu52C8|ofWcg6&Rp*Opmd1mv#%cM{5}#JOn_XrU2R&YSh5}phMjqqSpxF$~9XUti*UsR^HolYPepL2d=J<faRcNzrrUi@d@Z?BNMf$SKTp
U4lGNDi08|SK&Unec7RL2PHISXpq@d_8K*D7b>YPC+VVJG;wa#>nld)!+aEr#sQrUcCMAMxP9$U+%l1W&+9w3>KCkMzH&WmC$cEmqwt-guApXD^6iEO!MOcX
spj^po}R;`-
)tdT|CHrAk~+u1=?1A+M&Fm*;=!&C&nALixXcg>tE1SXXDjSt!IX3WKLsu7SERMp>$TF9~8n_o6uuJ>)HZoGK|I<wsI<W4&_syuCq*C3*!{cF@$5yQTuar&=
kvrY8CwOmUvAwI(^-
U*eCr^jyZ4_@Raj1e<Y3dOIVpc5A3kmCBqm^9P2KA9Kg0CpJ8?qz!H|i#Q!5=!B%s{TbY)zit&2Gia+Y`=;?v<EY=X3ZCEXN;Udz3Qm5G)#%BINbpKs{_7zP
WQrVfS30Gue=VUr3Lp}lAj06eiNI@w+?6~LWW0_x;ni_AG&?nfafl1ywYMj(<nCWfAP;bGLNbpv1cCviFlKiWvG1}N0hyY0z#cL1UbUs+;%(P$?}uq^RqMv7
Drym4bLE9*$ehq|UA=Q{-;fw7Ll$)?Y6n>BthUCL%}T-aZ(Rx%^J+GHi)gI4>v?0}8Lt&%D*uV2RRU0m+-
ROc%(_$KU^j0Z)HzlY<moabYSw?D40Vi>ROr8xu}(^IQg)USIkMd5R+XBVEuvMqW%Bi6A}0PBF%c+~n=RCCeo{s@F=m5s)Wz?cV)#-
Ve|36&{Znzgs8|iREFdc>-mZo$(ci>&n0QgVIK>DJ@KU5!f|D-b+YtafSFf`zvA`^WiZzr@75bi6oLj{KdNri26(DL5%=3zL35Q-
RX=~Ml8XQigTD=)p6FuC|mpLH3e+@kMoMm`XFsOkSp+I?n%=?QYUP^l>H4cW$k0pq$^S$kIzMb;Et#ZGe^S>Q(z^(GY^|_$R2Y(_bY{&~`cBkcrnz=31AS(8
@RKZZF3PzPosOlo6K5Q7tXmGLYkvpfn$b;Egx#XecmfNM2b+tJ#qP#fwN;|r_{Dr@`z!8d8B~d-
Y2^$J+#T_O38n*Nm(<dzOx@go(4T&PU8^6xr*RG?{tF*=KQ<`%3HN44b>WV(n>yM}F%domm?N}?Va*!i4=6HkHj-TqTV~N>?ykkz<svZWIUHYw1!rH~k3w12
WUt(00VfIr0vvI4Vu1syTSPM0<9$d|qrN#SH$d7y;(Wxi!Z2QY1auxEHMPd{Pq(1s)8p=f|`fWc+QM<!`>rYVBF8@HuUbPCfb5TeR%-
e)#)RuZPJ^gZhemVVYoqqjraYF`{9|Pr<n1~il*--
*|vhpD>SDme3Qpj3ZSEn~0v2&=(dWB;vZWmFaJm=Sv==fIrzMjE*Hq~!+a7LGnFR@lp(AG?_9(n6czlynAH(l@IP}cvrWYwwQ4H{8>=0AF2p~_)TGl6pb+xs
sKWkp>""".replace('\n', '')
raw = zlib.decompress(base64.b85decode(PAYLOAD_B85.encode('ascii')))
if hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA256:
    raise RuntimeError('V15 payload SHA-256 drift')
exec(compile(raw, str(Path(__file__).resolve()), 'exec'), globals(), globals())
