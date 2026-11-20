#!/usr/bin/env python3
"""Arithmetic source-consistency audit ONLY (not a first-sighting model validation).
Primary original: https://astro.bas.bg/AIJ/issues/n16/08_MNikifor2.pdf
Printed pp. 56 Fig.4, 57 Eqs.2a-3b, 58 prose. No observational data fitted.
"""
from decimal import Decimal
import json

D = Decimal

def numbers():
    h = D('-14')
    m = D('5.28')
    # Page 57 literal eq (3a) and eq (3b), seen on original-page screenshot.
    p57_lit_3a = D('-2.78')-D('0.18')*h
    p57_lit_3b = D('15.62')-D('6.61')*m
    # Page 56 Fig.4 plotted labels, 5.61 reiterated on p.58.
    fig4_3a = D('2.78')-D('0.18')*h
    fig4_3b = D('15.62')-D('5.61')*m
    # Crossover: evaluate bright equation at split and plotted faint equation.
    split_h = D('-7.7')
    bright_at_split = D('-1.95')-D('0.80')*split_h
    faint_at_split = D('2.78')-D('0.18')*split_h
    literal_at_split = D('-2.78')-D('0.18')*split_h
    return {
      'kind':'PUBLISHED_EQUATION_INTERNAL_CONSISTENCY__NOT_MODEL_VALIDATION',
      'original_url':'https://astro.bas.bg/AIJ/issues/n16/08_MNikifor2.pdf',
      'original_printed_pages':['56 Fig.4','57 Eqs. 2a-3b','58 discussion'],
      'input_sun_altitude_deg':str(h),'input_magnitude':str(m),
      'p57_3a_literal_mag':str(p57_lit_3a),
      'figure4_3a_mag':str(fig4_3a),
      'difference_magnitude':str(fig4_3a-p57_lit_3a),
      'p57_3b_literal_solar_altitude_deg':str(p57_lit_3b),
      'figure4_and_p58_3b_solar_altitude_deg':str(fig4_3b),
      'difference_solar_altitude_deg':str(fig4_3b-p57_lit_3b),
      'split_at_h_minus_7_7_bright_eq_mag':str(bright_at_split),
      'split_at_h_minus_7_7_plotted_faint_eq_mag':str(faint_at_split),
      'split_at_h_minus_7_7_p57_literal_faint_eq_mag':str(literal_at_split),
      'printed_domain_2b':'m > 4.2 (contradicts bright-star branch)',
      'printed_domain_3b':'m <= 4.2 (contradicts faint-star branch)',
      'p58_5_61':'yes, confirms Figure 4 slope but also says if m_prime < 4.2 (reverse branch)',
      'individual_first_sighting_validated_cases':0,
      'scope':'The authors fit curves to own selected observations; individual late-star time, NON_SEEN, sky/aerosol/adaptation metadata absent. Do not infer model error or validate 10.5-16 degrees.'
    }

def self_test():
    r=numbers()
    assert r['p57_3a_literal_mag']=='-0.26'
    assert r['figure4_3a_mag']=='5.30'
    assert r['difference_magnitude']=='5.56'
    assert r['p57_3b_literal_solar_altitude_deg']=='-19.2808'
    assert r['figure4_and_p58_3b_solar_altitude_deg']=='-14.0008'
    assert r['difference_solar_altitude_deg']=='5.2800'
    assert r['split_at_h_minus_7_7_bright_eq_mag']=='4.210'
    assert r['split_at_h_minus_7_7_plotted_faint_eq_mag']=='4.166'
    assert r['split_at_h_minus_7_7_p57_literal_faint_eq_mag']=='-1.394'
    assert r['individual_first_sighting_validated_cases']==0
    return 10

if __name__ == '__main__':
    n=self_test()
    print(json.dumps(numbers(), indent=2, ensure_ascii=False))
    print('SOURCE_ARITHMETIC_TESTS_PASS', n)
