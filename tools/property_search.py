"""Address and parcel-number matching over the current local parcel snapshot."""
import re

ABBREVIATIONS={'drive':'dr','street':'st','avenue':'ave','boulevard':'blvd','road':'rd','court':'ct','lane':'ln','circle':'cir','parkway':'pkwy','north':'n','south':'s','east':'e','west':'w'}

def words(value):
    return [ABBREVIATIONS.get(t,t) for t in re.findall(r'[^\W_]+',str(value or '').casefold())]

def search_parcels(rows,query):
    if not isinstance(query,str) or len(query)>160:raise ValueError('Search must be at most 160 characters')
    tokens=words(query)
    if not tokens:return []
    text=' '.join(tokens);digits=''.join(c for c in query if c.isdigit());printed=query.strip().split('-')
    pins={digits} if len(digits)>=5 and not any(c.isalpha() for c in query) else set()
    if len(printed)==6 and [len(p) for p in printed]==[2,2,2,4,2,3] and all(p.isdigit() for p in printed):pins.add(printed[2]+printed[1]+printed[0]+''.join(printed[3:]))
    matches=[]
    for row in rows:
        props=row.get('properties',row);address_words=words(props.get('site_address'));address=' '.join(address_words);pin=str(props.get('parcel_id') or '')
        score=0
        if pin and pin in pins:score=100
        elif address==text:score=95
        elif address.startswith(text):score=80
        elif all(any(part.startswith(token) for part in address_words) for token in tokens):score=60
        elif pins and any(part in pin for part in pins):score=40
        if score:matches.append((score,address,pin,str(props.get('id') or row.get('id') or ''),row))
    return [item[-1] for item in sorted(matches,key=lambda item:(-item[0],item[1],item[2],item[3]))]
