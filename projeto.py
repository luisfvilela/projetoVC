import cv2
import mediapipe as mp
import numpy
import math
import subprocess
import time
import argparse
from pynput.keyboard import Key, Controller
teclado = Controller()

parser = argparse.ArgumentParser(description="Controlador de Musica utilizando Visão Computacional")
parser.add_argument("-b", "--background",action="store_true")
iterativo = not parser.parse_args().background

def main():
# Inicializando os módulos do MediaPipe
    mp_maos = mp.solutions.hands
    mp_desenho = mp.solutions.drawing_utils

# Configurando o modelo: 
# min_detection_confidence e min_tracking_confidence ajudam a evitar falsos positivos
    maos = mp_maos.Hands(
        max_num_hands=1, # Detectar apenas uma mão por vez para simplificar
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

# Abrindo a webcam (0 é a câmera padrão)
    cap = cv2.VideoCapture(0)

    print("Pressione 'q' no terminal ou na janela para sair.")

    cmd = "pactl get-sink-volume @DEFAULT_SINK@ | grep -o '[0-9]*%' | sed -n '1 s/%//p'"
# Variaveis para movimento
    volume = int(subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout)
    yAnterior = None
    SENS_BASE = 150
    LIMIAR_PINCA = 0.05
    COOLDOWN_PLAY = 1.0
    ultimo_comando_tempo = 0
    contador = 0
    tolerancia_next_previous = 25
    sensibilidade_volume = 350

    while cap.isOpened():
        sucesso, frame = cap.read()
        if not sucesso:
            print("Ignorando frame vazio da câmera.")
            continue
        
        frame = cv2.flip(frame,1)
        # O OpenCV usa BGR por padrão, mas o MediaPipe precisa de RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Processa a imagem para encontrar as mãos
        resultado = maos.process(frame_rgb)

        tem_pinca = False
        gesto_atual = "Nenhum"
        tempo_atual = time.time()

        # Se encontrou alguma mão na tela
        if resultado.multi_hand_landmarks:
            for landmarks in resultado.multi_hand_landmarks:
                # Desenha os pontos e as conexões na imagem (opcional, bom para debugar)
                if iterativo:
                    mp_desenho.draw_landmarks(frame, landmarks, mp_maos.HAND_CONNECTIONS)

                # LÓGICA DO GESTO: Mão aberta vs Mão fechada
                # Pegamos a ponta dos dedos (índice 8, 12, 16, 20) e comparamos 
                # com a junta do meio do dedo (índice 6, 10, 14, 18).
                # No eixo Y, o topo da tela é 0. Se a ponta do dedo tem um Y MENOR que a junta,
                # significa que o dedo está levantado.
                
                h , w , _ = frame.shape

                dedos_levantados = 0

                polegar = landmarks.landmark[4]            
                indicador = landmarks.landmark[8]
                centro_mao = landmarks.landmark[9].y

                distanciaPinca = math.sqrt((polegar.x - indicador.x)**2 + (polegar.y - indicador.y)**2)
                distanciaResto = math.sqrt((landmarks.landmark[12].x - indicador.x)**2 + (landmarks.landmark[12].y - indicador.y)**2)
                if distanciaPinca <= LIMIAR_PINCA and distanciaResto >= 2*LIMIAR_PINCA:
                    tem_pinca = True
                    if(yAnterior == None):
                        yAnterior = centro_mao
                        continue
                    
                    vetDirecao = numpy.array([landmarks.landmark[9].x - landmarks.landmark[16].x, landmarks.landmark[9].y - landmarks.landmark[16].y])
                    versorDirecao = vetDirecao / numpy.linalg.norm(vetDirecao)
                    angulo = numpy.array([1,0]).dot(versorDirecao)
                    sens = max(angulo,0) - 0.5
                    
                    deltaY = yAnterior - centro_mao 
                    volume += deltaY * (SENS_BASE + sens * SENS_BASE)
                    volume = max(0, min(volume, 100))
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{int(volume)}%"])


                    gesto_atual = "Pinca : Volume " + str(volume) +  " Sensibilidade: " + str(sens)
                    yAnterior = centro_mao
                    continue



                yAnterior = None

                # Índices das pontas: Indicador(8), Médio(12), Anelar(16), Mindinho(20)
                pontas = [8, 12, 16, 20]
                juntas = [6, 10, 14, 18]
                
                for ponta, junta in zip(pontas, juntas):
                    if landmarks.landmark[ponta].y < landmarks.landmark[junta].y:
                        dedos_levantados += 1
                
                # Lógica para o polegar (o eixo X é melhor para o polegar do que o Y)
                # Dica: Essa lógica do polegar inverte dependendo da mão (esquerda/direita), 
                # mas simplificaremos focando nos outros 4 dedos.
                
                

                if dedos_levantados == 4:
                    gesto_atual = "Mao Aberta (Pausar/Play)"
                    if (tempo_atual - ultimo_comando_tempo) > COOLDOWN_PLAY:
                        # Simula a tecla física multimídia (bypassa bugs do Deezer Lite)
                        #teclado.press(Key.media_play_pause)
                        #teclado.release(Key.media_play_pause)
                        subprocess.run(["playerctl", "play-pause"])
                        print("Comando enviado. Verifique se a música tocou/pausou.")
                        ultimo_comando_tempo = tempo_atual

                elif dedos_levantados == 0:
                    gesto_atual = "Mao Fechada (Mudo)"

                elif dedos_levantados == 1 and (tempo_atual - ultimo_comando_tempo) > COOLDOWN_PLAY:
                    gesto_atual = "Um dedo"
                    if gesto_atual!="Um dedo":
                        contador=0
                        continue
                    contador+=1
                    if contador<tolerancia_next_previous:
                        continue
                    #teclado.press(Key.media_next)
                    #teclado.release(Key.media_next)
                    subprocess.run(["playerctl", "next"])
                    ultimo_comando_tempo = tempo_atual
                    contador = 0

                elif dedos_levantados == 2 and (tempo_atual - ultimo_comando_tempo) > COOLDOWN_PLAY:
                    gesto_atual = "Dois dedos"
                    if gesto_atual!="Dois dedos":
                        contador=0
                        continue
                    contador+=1
                    if contador<tolerancia_next_previous:
                        continue
                    
                    #teclado.press(Key.media_previous)
                    #teclado.release(Key.media_previous)
                    subprocess.run(["playerctl", "previous"])
                    ultimo_comando_tempo = tempo_atual
                    contador = 0

                else:
                    gesto_atual = f"Gesto Desconhecido ({dedos_levantados} dedos)"

        if iterativo:
            desenhar_hud_volume(frame, volume, tem_pinca)

        # Mostra o frame final na tela
        if iterativo:
            cv2.imshow('Rastreamento de Gestos', frame)
        print(f"Gesto Detectado: {gesto_atual}".ljust(50), end='\r')

        # Sai do loop se apertar 'q'
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

# Limpeza
    print("\nEncerrando...")
    cap.release()
    cv2.destroyAllWindows()

def desenhar_hud_volume(frame, volume, tem_pinca):
    """
    Desenha a barra de volume e a porcentagem diretamente no frame do OpenCV.
    """
    # Coordenadas fixas da barra lateral
    x1, y1 = 50, 150   # Canto superior esquerdo
    x2, y2 = 85, 400   # Canto inferior direito

    # 1. Desenha o contorno da barra (Fundo cinza escuro)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (60, 60, 60), 3)

    # 2. Calcula a altura proporcional do preenchimento
    altura_dinamica = int(y2 - (volume * (y2 - y1) / 100))

    # 3. Define a cor baseada no estado da pinça (Verde ativa / Azul inativa)
    cor_barra = (0, 255, 0) if tem_pinca else (255, 0, 0)

    # 4. Desenha o retângulo preenchido
    if volume > 0:
        cv2.rectangle(frame, (x1, altura_dinamica), (x2, y2), cor_barra, cv2.FILLED)

    # 5. Adiciona o texto do percentual acima da barra
    cv2.putText(
        frame, 
        f"{int(volume)}%", 
        (x1 - 5, y1 - 15), 
        cv2.FONT_HERSHEY_SIMPLEX, 
        0.7, 
        (255, 255, 255), 
        2
    )

main()
