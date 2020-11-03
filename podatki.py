import orodja
import os
import re
import requests
import time

def cleanup(title, data):
    '''
    data = (
        type,
        episodes,
        status,
        premiered,
        producers,
        licensors,
        studios,
        source,
        genres,
        duration,
        rating,
        score,
        votes
        )

    return clean_data := [
        'title'     : Str
        'type'      : Str
        'episodes'  : Int
        'status'    : Str
        'premiered' : Str
        'producers' : [Str]
        'licensors' : [Str]
        'studios'   : [Str]
        'source'    : Str
        'genres'    : [Str]
        'duration'  : Int
        'rating'    : Str
        'score'     : Float
        'votes'     : Int
    ]
    '''
    title = title
    series_type = data[0]
    episodes = int(data[1]) if data[1] else None
    status = data[2]

    premiered = data[3]

    producers = cleanup_title_re.findall(data[4]) or []
    licensors = cleanup_title_re.findall(data[5]) or []
    studios = cleanup_title_re.findall(data[6]) or []

    source = data[7]

    genres = cleanup_title_re.findall(data[8]) or []

    h1, m1, m2 = cleanup_duration_re.findall(data[9])[0]
    if m2:
        duration = int(m2)
    else:
        total = 0
        if h1:
            total += 60 * int(h1)
        if m1:
            total += int(m1)
        duration = total if total else None


    rating = data[10].replace('amp;', '') if data[10] else None
    score = float(data[11]) if data[11] else None
    votes = int(data[12].replace(',', '')) if data[12] else None

    clean_data = {
        'title'      : title,
        'series_type': series_type,
        'episodes'   : episodes,
        'status'     : status,
        'premiered'  : premiered,
        'producers'  : producers,
        'licensors'  : licensors,
        'studios'    : studios,
        'source'     : source,
        'genres'     : genres,
        'duration'   : duration,
        'rating'     : rating,
        'score'      : score,
        'votes'      : votes
    }
    return clean_data

cleanup_title_re = re.compile(r'title="(.*?)"')
cleanup_duration_re = re.compile(r'(?:([0-9]+) hr\. ([0-9]+) min\.)|(?:([0-9]+) min\.)')

def block_match(block):
    li = []
    for reg in block_match_regexes[:-1]:
        val = reg.findall(block)
        if val:
            li.append(val[0])
        else:
            li.append(None)
    v = block_match_regexes[-1].findall(block)
    if v:
        score, votes = v[0]
        li.append(score)
        li.append(votes)
    else:
        li.append(None)
        li.append(None)
    return li

re_data = [
        r'Type:</span>.*?>(.*?)</a></div>.*?',
        r'Episodes:</span>\n.*?(?:([0-9]+)|(?:Unknown))\n.*?</div>.*?',
        r'Status:</span>.*?\b(.*?)\n.*?</div>.*?',
        r'Premiered:</span>.*?>(.*?)</a>.*?',
        r'Producers:</span>.*?\n(.*?)\n.*?',
        r'Licensors:</span>.*?\n(.*?)\n.*?',
        r'Studios:</span>.*?\n(.*?)\n.*?',
        r'Source:</span>.*?\b(.*?)\n.*?</div>.*?',
        r'Genres:</span>.*?\n(.*?)\n.*?',
        r'Duration:</span>.*?\b(.*?)\n.*?</div>.*?',
        r'Rating:</span>.*?\b(.*?)\n.*?</div>.*?',
        r'Score:</span>.*?class="score.*?>(.*?)</span>.*?</span>(.*?) users\)\n.*?</div>.*?'
    ]
block_match_regexes = [re.compile(pattern, flags=re.DOTALL) for pattern in re_data]

#-----------------------------------------------------------------------------------------
# Lokacije in shranjevanje glavne strani

def main():
    homepage_url = 'https://myanimelist.net/topanime.php?type=bypopularity'

    data_dir = 'data'
    homepage_filename = os.path.join(data_dir, 'homepage.html')

    download = True
    if os.path.isdir(data_dir):
        msg = 'Direktorij s podatki že obstaja. Ali želite ponovno naložiti vse podatke? [Y/N]: '
        while True:
            response = input(msg).upper()
            if response not in 'YN':
                continue
            download = response == 'Y'
            break
    if not download:
        return None

    warning_msg = (
        'REGEX lahko in bo narobe preberal nekatere strani, preveri na hitro končne podatke. '
        f'Url-ji, iz katerih podatki sploh niso v .csv datotekah, se nahajajo v {data_dir}/fails.'
    )
    print(warning_msg)

    orodja.shrani_spletno_stran(homepage_url, homepage_filename)

#-----------------------------------------------------------------------------------------
# Shranjevanje url-jev, kjer se nahajajo podatki

    series_urls = []
    series_pattern = r'<h3 class="hoverinfo_trigger.*?href="(.*?)".*?>(.*?)</a>'
    comp_re_series = re.compile(series_pattern)

    session = requests.Session()

    LIMIT = 10000
    for limit in range(0, LIMIT, 50):
        print(f'{100 * (limit + 50) / LIMIT}% začetnega prenašanja')

        time.sleep(2)
        page_url = homepage_url + f'&limit={limit}'
        r = session.get(page_url)

        for match in comp_re_series.findall(r.text):
            series_urls.append((match[0], match[1]))

#-----------------------------------------------------------------------------------------
# Prebiranje podatkov iz url-jev

    re_block = r'<h2>Information</h2>.*?</div></td>'
    comp_re_block = re.compile(re_block, flags=re.DOTALL)

    rows = []

    fails = []
    for idx, (url, title) in enumerate(series_urls):
        try:
            time.sleep(2)
            print(f'{100 * (idx + 1) / LIMIT}% končnega prenašanja')
            r = session.get(url)
            page = r.text

            block = comp_re_block.findall(page)[0]
            data = block_match(block)

            rows.append(cleanup(title, data))
        except Exception:
            fails.append(url)
            continue

    orodja.pripravi_imenik(data_dir)
    with open(os.path.join(data_dir, 'fails'), 'w') as f:
        for url in fails:
            f.write(f'{url}\n')
#-----------------------------------------------------------------------------------------
# Sortiranje prečiščenih podatkov v vrste za csv datoteke

    main_headers = [
        'title',
        'series_type',
        'episodes',
        'status',
        'premiered',
        'source',
        'duration',
        'rating',
        'score',
        'votes'
    ]

    main_rows = []
    producer_rows = []
    licensor_rows = []
    studio_rows = []
    genre_rows = []

    for row in rows:
        new_row = {}

        for key, value in row.items():
            if key in main_headers:
                new_row[key] = value

            elif key == 'producers':
                for producer in value:
                    producer_rows.append({'title': row['title'], 'producer': producer})

            elif key == 'licensors':
                for licensor in value:
                    licensor_rows.append({'title': row['title'], 'licensor': licensor})

            elif key == 'studios':
                for studio in value:
                    studio_rows.append({'title': row['title'], 'studio': studio})

            elif key == 'genres':
                for genre in value:
                    genre_rows.append({'title': row['title'], 'genre': genre})

        main_rows.append(new_row)

#-----------------------------------------------------------------------------------------
# pisanje podatkov v csv datoteke

    main_csv_name = 'serije.csv'
    orodja.zapisi_csv(main_rows, main_headers, os.path.join(data_dir, main_csv_name))

    producer_csv_name = 'producerji.csv'
    orodja.zapisi_csv(producer_rows, ['title', 'producer'], os.path.join(data_dir, producer_csv_name))

    licensor_csv_name = 'licensorji.csv'
    orodja.zapisi_csv(licensor_rows, ['title', 'licensor'], os.path.join(data_dir, licensor_csv_name))

    studio_csv_name = 'studiji.csv'
    orodja.zapisi_csv(studio_rows, ['title', 'studio'], os.path.join(data_dir, studio_csv_name))

    genre_csv_name = 'žanri.csv'
    orodja.zapisi_csv(genre_rows, ['title', 'genre'], os.path.join(data_dir, genre_csv_name))



if __name__ == '__main__':
    main()