api_id = 24364263  #25965329
api_hash = "1f03c4f0e8617dd5fe4f16e9d629f47c" #"6604012087bc1273f1f918571c02af24"

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
    2204843457: { #Crypto Master | Futures Signals
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'SamCrypto_Master': 'parampam',
        },
    },
    4593819858: { #Crypto Master | Futures Signals
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
channels_to_send = [2204843457, 2170620330] #, 

replacements_in_images = { # ключи (первое слово) в нижнем регистре!
    '@samcrypto_master': '@ParamPam',
}

# Пример вызова функции
# processed_images = find_and_replace_in_images(
#     ["image1.jpg", "image2.jpg", "image3.jpg"],  # Путь к изображениям
#     "template_image.jpg",  # Путь к изображению-шаблону
#     "replacement_image.jpg"  # Путь к изображению для замены
# )

