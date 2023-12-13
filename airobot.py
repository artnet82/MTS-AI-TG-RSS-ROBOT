 import argparse
import random
from configparser import ConfigParser
from pprint import pprint
import wave

import grpc
from google.protobuf.json_format import MessageToDict
from keycloak import KeycloakOpenID
from telegram import Bot

import tts_pb2
import tts_pb2_grpc


def read_api_config(file_name: str = "config.ini") -> ConfigParser:
    """
    Читает конфигурацию API из файла и возвращает объект ConfigParser с настройками API.
    """
    config = ConfigParser()
    config.read(file_name)

    return config


def get_request_metadata(auth_config: dict[str, str]) -> list[tuple[str, str]]:
    """
    Создает метаданные запроса с помощью модуля KeycloakOpenID для аутентификации и авторизации запроса.
    """
    sso_connection = KeycloakOpenID(
        auth_config["sso_server_url"],
        auth_config["realm_name"],
        auth_config["client_id"],
        auth_config["client_secret"],
        verify=True,
    )
    token_info = sso_connection.token(grant_type="client_credentials")
    access_token = token_info["access_token"]

    trace_id = str(random.randint(1000, 9999))
    print(f"Trace id: {trace_id}")

    metadata = [
        ("authorization", f"Bearer {access_token}"),
        ("external_trace_id", trace_id),
    ]

    return metadata


def synthesize_stream(text: str, api_address: str, auth_config: dict[str, str]):
    """
    Отправляет текстовый запрос на сервер gRPC с настройками синтеза речи
    и получает аудиоответ в виде потока, сохраняя его в файл 'synthesized_audio.wav'.
    """
    sample_rate = 22050
    request = tts_pb2.SynthesizeSpeechRequest(
        text=text,
        encoding=tts_pb2.AudioEncoding.LINEAR_PCM,
        sample_rate_hertz=sample_rate,
        voice_name="gandzhaev",
        synthesize_options=tts_pb2.SynthesizeOptions(
            postprocessing_mode=tts_pb2.SynthesizeOptions.PostprocessingMode.POST_PROCESSING_DISABLE,
            model_type="default",
            voice_style=tts_pb2.VoiceStyle.VOICE_STYLE_NEUTRAL,
        ),
    )
    print("Подготовленный запрос:")
    pprint(MessageToDict(request))

    options = [
        ("grpc.min_reconnect_backoff_ms", 1000),
        ("grpc.max_reconnect_backoff_ms", 1000),
        ("grpc.max_send_message_length", -1),
        ("grpc.max_receive_message_length", -1),
    ]

    credentials = grpc.ssl_channel_credentials()

    print(f"\nОтправка запроса на gRPC-сервер {api_address}")

    with grpc.secure_channel(
        api_address, credentials=credentials, options=options
    ) as channel:
        stub = tts_pb2_grpc.TTSStub(channel)

        request_metadata = get_request_metadata(auth_config)

        response_iterator = stub.StreamingSynthesize(
            request,
            metadata=request_metadata,
            wait_for_ready=True,
        )

        print("Метаданные ответа:")
        initial_metadata = dict(response_iterator.initial_metadata())
        print(f"request_id={initial_metadata.get('request_id', '')}")
        print(f"trace_id={initial_metadata.get('external_trace_id', '')}")

        path = "synthesized_audio.wav"
        wave_data = wave.open(path, "wb")
        wave_data.setnchannels(1)
        wave_data.setframerate(sample_rate)
        wave_data.setsampwidth(2)

        for idx, chunk in enumerate(response_iterator, 1):
            print(f"Получен чанк #{idx} размером {len(chunk.audio)} байт")
            wave_data.writeframesraw(chunk.audio)

        wave_data.close()

        print(f"Сохранен полученный аудиофайл в {path}")

        return path


def send_audio_to_telegram(bot_token: str, chat_id: str, audio_file: str):
    """
    Отправляет аудиофайл через Telegram, используя бота с указанным токеном и идентификатором чата.
    """
    bot = Bot(token=bot_token)
    bot.send_audio(chat_id=chat_id, audio=open(audio_file, "rb"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("text", type=str, help="текст для синтеза речи")

    args = parser.parse_args()

    
