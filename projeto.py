import cv2
import mediapipe as mp
import math

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

# Variaveis para movimento
yAnterior = None
LIMIAR_PINCA = 0.05

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

    # Se encontrou alguma mão na tela
    if resultado.multi_hand_landmarks:
        for landmarks in resultado.multi_hand_landmarks:
            # Desenha os pontos e as conexões na imagem (opcional, bom para debugar)
            mp_desenho.draw_landmarks(frame, landmarks, mp_maos.HAND_CONNECTIONS)

            # LÓGICA DO GESTO: Mão aberta vs Mão fechada
            # Pegamos a ponta dos dedos (índice 8, 12, 16, 20) e comparamos 
            # com a junta do meio do dedo (índice 6, 10, 14, 18).
            # No eixo Y, o topo da tela é 0. Se a ponta do dedo tem um Y MENOR que a junta,
            # significa que o dedo está levantado.
            
            dedos_levantados = 0

            polegar = landmarks.landmark[4]            
            indicador = landmarks.landmark[8]
            centro_mao = landmarks.landmark[9].y

            distanciaPinca = math.sqrt((polegar.x - indicador.x)**2 + (polegar.y - indicador.y)**2)
            distanciaResto = math.sqrt((landmarks.landmark[12].x - indicador.x)**2 + (landmarks.landmark[12].y - indicador.y)**2)
            if distanciaPinca <= LIMIAR_PINCA and distanciaResto >= 2*LIMIAR_PINCA:
                tem_pinca = True
                gesto_atual = "pinca"
                
                continue




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
            elif dedos_levantados == 0:
                gesto_atual = "Mao Fechada (Mudo)"
            else:
                gesto_atual = f"Gesto Desconhecido ({dedos_levantados} dedos)"

    # Mostra o frame com os desenhos
    cv2.imshow('Rastreamento de Gestos', frame)
    
    # Printa o gesto detectado no terminal
    # O \r faz o print sobrescrever a mesma linha no terminal, mantendo limpo
    print(f"Gesto Detectado: {gesto_atual}".ljust(50), end='\r')

    # Sai do loop se apertar 'q'
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

# Limpeza
print("\nEncerrando...")
cap.release()
cv2.destroyAllWindows()
