api_id = 22900607  #25965329
api_hash = "2101d7377e8f53d4d356ba1485d79eeb" #"6604012087bc1273f1f918571c02af24"
# bot_token = '7658487162:AAEmSzNUCZ2caOp2rxuo6DeL8Vfcu-aehaA'

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
     
}

#каналы куда отсылаем#
channels_to_send = [2313168509] #, 2170620330

replacements_in_images = { # ключи (первое слово) в нижнем регистре!
    '@samcrypto_master': '@ParamPam',
}

# # Словарь с заменами (текущий текст кнопки -> новая ссылка)
# replacements_in_buttons = {
#     'PLAY NOW': 'https://www.wikipedia.org',
#     'Announcements': 'https://www.reddit.com',
#     'Join Community': 'https://www.reddit.com',
#     'FAQ': 'https://www.reddit.com'
# }



