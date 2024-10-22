api_id = 22900607 #25965329
api_hash = '2101d7377e8f53d4d356ba1485d79eeb' #"6604012087bc1273f1f918571c02af24"
bot_token = '7738836203:AAHY-A-TUXd-izs-zP8DlsBandrxgjf5OGw' #'7905362232:AAHV2il7ogCFpRLDmM92pLhHYXBsIf87-_M'

name_session_client = 'sessionTC'
name_session_bot = 'sessionBot'

#каналы которые слушаем без -100!
channels_to_listen = {
    2023070684: { #Crypto Master | Futures Signals
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'SamCrypto_Master': 'reach_me_here',
            'Sam':'reach_me_here',
        },
        'channels_to_send': [-1002313168509] #каналы куда отсылаем каналы с -100
    },
     2009977255: { #Victor Trader
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'Victor Trader': 'reach_me_here',
            'Victor': 'reach_me_here',
            '@reach_me_here':'https://www.binance.com',
            'https://t.me/c/2009977255/12895':'https://www.binance.com',
            'https://bit.ly/safebestbroker':'https://bit.ly/4gK7frD',
            'https://t.me/victortraderofficialsupport':'@reach_me_here',
            'https://t.me/c/2009977255/13812':'https://www.binance.com',
        },
        'channels_to_send': [-1002291645140] #каналы куда отсылаем каналы с -100
    },   
}


replacements_in_images = { # ключи (первое слово) в нижнем регистре!
    '@samcrypto_master': '@reach_me_here',
}

# # Словарь с заменами (текущий текст кнопки -> новая ссылка)
replacements_in_buttons = {
     'OPEN BROKER': 'https://bit.ly/4gK7frD',
     'CONTACT SUPPORT': 'https://bit.ly/4gK7frD',
     '⤴️ SHARE RESULTS': 'https://www.binance.com',
     'FAQ': 'https://www.binance.com'
 }

replacement_urls = { # если ссылка содержит в себе первое слово, то вся она меняется на второе слово
    "bingx": "https://www.binance.com",
    "t.me": "https://www.binance.com",
}



