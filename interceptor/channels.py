api_id = 24364263  #25965329
api_hash = "1f03c4f0e8617dd5fe4f16e9d629f47c" #"6604012087bc1273f1f918571c02af24"
bot_token = '7658487162:AAEmSzNUCZ2caOp2rxuo6DeL8Vfcu-aehaA'

#каналы которые слушаем#
channels_to_listen = {
    2023070684: { #Crypto Master | Futures Signals
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'SamCrypto_Master': 'parampam',
        },
    },
    1242446516: { #	Україна 24/7
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'SamCrypto_Master': 'parampam',
        },
    },
    #2204843457: { #Crypto Master | Futures Signals
    #    'moderation_if_image': False,
    #    'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
    #    'replacements': {
    #        'bingx': 'google',
    #        'Bingx': 'Google',
    #        'SamCrypto_Master': 'parampam',
    #    },
    #},
    4593819858: { #Crypto Master | Futures Signals
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'SamCrypto_Master': 'parampam',
        },
    },
     1146915409: { #Binance Announcements
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'SamCrypto_Master': 'parampam',
        },
    },
    
    
}

#каналы куда отсылаем#
channels_to_send = [2204843457] #, 2170620330

replacements_in_images = { # ключи (первое слово) в нижнем регистре!
    '@samcrypto_master': '@ParamPam',
}

# Словарь с заменами (текущий текст кнопки -> новая ссылка)
replacements_in_buttons = {
    'PLAY NOW': 'https://www.wikipedia.org',
    'Announcements': 'https://www.reddit.com',
    'Join Community': 'https://www.reddit.com',
    'FAQ': 'https://www.reddit.com'
}



