import streamlit as st
from PIL import Image
import numpy as np
import os
import tempfile
import math
from rembg import remove # Importa a função de remover fundo

# --- 1. CORREÇÃO CRÍTICA DE ERRO (PIL/Pillow > 9.0) ---
try:
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except AttributeError:
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip

# --- 2. FUNÇÃO PRINCIPAL DE GERAÇÃO DE VÍDEO (CUTOUT ANIMATION) ---
def create_cartoon_animation(parts, duration_sec, fps):
    """
    Cria uma animação de recortes (cutout animation) a partir de clipes de partes separadas.
    """
    try:
        clip_duration = duration_sec
        final_clips = []
        
        # ----------------------------------------------------------------------
        # PONTOS DE PIVÔ E MOVIMENTO (Para ajuste fino após o primeiro deploy)
        # ----------------------------------------------------------------------
        
        # Posições de Conexão no Corpo Base (ajustadas para o centro da peça)
        # Assumimos que as peças foram cortadas de forma que o ponto de pivô desejado esteja no centro horizontal
        # e na parte superior para braços/cabeça ou parte superior-central para pernas
        
        # Estes são pontos relativos ao tamanho total do corpo base
        OMBRO_ESQ_X_REL = 0.35 # Mais à esquerda
        OMBRO_DIR_X_REL = 0.65 # Mais à direita
        OMBRO_Y_REL = 0.35
        QUADRIL_Y_REL = 0.65

        # Frequências e Amplitudes para balanço
        SWAY_FREQ = 1.0 # Balanço principal do corpo (1 ciclo por segundo)
        WALK_FREQ = 2.0 # Frequência de marcha (2 ciclos por segundo)
        BREATH_AMP = 5 # Amplitude de subida/descida (pixels)
        SWAY_ROT_AMP = 0.5 # Amplitude de rotação (graus)

        # ----------------------------------------------------------------------
        # PASSO 3: ADICIONAR MOVIMENTO AO TRONCO E AO CORPO BASE (RESPIRAÇÃO E BALANÇO GERAL)
        # ----------------------------------------------------------------------
        
        if 'Tronco/Vestido' not in parts:
            st.error("É necessário carregar o arquivo 'Tronco/Vestido' para iniciar a animação.")
            return None
        
        np_base_body = np.array(parts['Tronco/Vestido'].convert("RGBA"))
        clip_base_body = ImageClip(np_base_body, duration=clip_duration)
        video_size = clip_base_body.size # Define o tamanho do vídeo com base no tronco
        
        # FUNÇÃO DE MOVIMENTO DO TRONCO
        def get_trunk_position(t):
            # Movimento suave vertical (simula respiração/balanço)
            y_offset = BREATH_AMP * math.sin(2 * math.pi * SWAY_FREQ * t) 
            return ('center', video_size[1]/2 + y_offset) # Posicionamento centralizado
            
        def get_trunk_rotation(t):
            # Rotação lateral suave
            return SWAY_ROT_AMP * math.sin(2 * math.pi * SWAY_FREQ * t / 2) # Frequência mais lenta

        clip_base_body = clip_base_body.set_position(get_trunk_position)
        # Para rotação de um clipe, ele rotaciona em torno de seu centro.
        # Se você deseja que ele gire em torno de um ponto específico,
        # o PNG da peça deve ter esse ponto como seu centro visual, ou
        # a rotação deve ser compensada com set_position.
        # Por simplicidade, mantemos a rotação no centro do clipe, o que funciona bem para o tronco.
        clip_base_body = clip_base_body.fx(lambda clip: clip.rotate(get_trunk_rotation(clip.start), resample='bicubic'))
        final_clips.append(clip_base_body)
        
        # --- Funções auxiliares para calcular posição e rotação com pivô ---
        def get_rotated_pos(t, part_clip, anchor_x_rel, anchor_y_rel, rotation_func):
            # Calcula o ponto de ancoragem no vídeo global
            anchor_global_x = video_size[0] * anchor_x_rel
            anchor_global_y = video_size[1] * anchor_y_rel

            # Ponto central original do clipe (se fosse sem rotação)
            clip_center_x = anchor_global_x
            clip_center_y = anchor_global_y

            # Rotaciona o clipe, mas queremos que o ponto de ancoragem permaneça fixo.
            # Isso é complexo com moviepy sem usar efeitos personalizados ou pré-processar imagens.
            # A abordagem mais simples é ajustar o PNG para ter o pivô no centro, ou aceitar
            # que a rotação ocorrerá no centro do recorte.
            # Para este exemplo, vamos assumir que as peças são desenhadas de forma a centralizar o pivô
            # ou que o descolamento é aceitável para o efeito "divertido".

            # A MoviePy rotaciona em torno do centro do *clip*.
            # Para que ele gire em torno de um ponto específico (ex: ombro),
            # o ideal é que a imagem do clipe tenha esse ponto como seu centro.
            # Alternativamente, podemos ajustar o set_pos para compensar a rotação,
            # mas isso exige saber a "alavanca" da peça em relação ao seu centro.

            # Por enquanto, vamos manter o set_pos no ponto de ancoragem e deixar a rotação acontecer
            # no centro do recorte, o que já dá um efeito de animação.
            # Para um controle de pivô perfeito, precisaríamos de uma lógica mais avançada
            # ou usar ferramentas como Krita/Spine para preparar os assets.

            return (clip_center_x - part_clip.w / 2, clip_center_y - part_clip.h / 2)


        # ----------------------------------------------------------------------
        # PASSO 4: PERNAS (MARCHA) - Movimento de balanço frontal/traseiro
        # ----------------------------------------------------------------------
        
        # PERNA 1 (Movimento em fase)
        if 'Perna 1' in parts:
            np_perna1 = np.array(parts['Perna 1'].convert("RGBA"))
            clip_perna1 = ImageClip(np_perna1, duration=clip_duration)
            
            def get_perna1_rotation(t):
                # Balança para frente e para trás
                return 15 * math.sin(2 * math.pi * WALK_FREQ * t)
            
            # Posicionamento no quadril esquerdo
            pos_perna1 = get_rotated_pos(0, clip_perna1, OMBRO_ESQ_X_REL, QUADRIL_Y_REL, get_perna1_rotation)
            clip_perna1 = clip_perna1.set_pos(pos_perna1)
            clip_perna1 = clip_perna1.fx(lambda clip: clip.rotate(get_perna1_rotation(clip.start), resample='bicubic'))
            final_clips.append(clip_perna1)

        # PERNA 2 (Movimento fora de fase)
        if 'Perna 2' in parts:
            np_perna2 = np.array(parts['Perna 2'].convert("RGBA"))
            clip_perna2 = ImageClip(np_perna2, duration=clip_duration)
            
            def get_perna2_rotation(t):
                # Balança para frente e para trás, mas com fase oposta (+pi)
                return 15 * math.sin(2 * math.pi * WALK_FREQ * t + math.pi)  
            
            # Posicionamento no quadril direito
            pos_perna2 = get_rotated_pos(0, clip_perna2, OMBRO_DIR_X_REL, QUADRIL_Y_REL, get_perna2_rotation)
            clip_perna2 = clip_perna2.set_pos(pos_perna2)
            clip_perna2 = clip_perna2.fx(lambda clip: clip.rotate(get_perna2_rotation(clip.start), resample='bicubic'))
            final_clips.append(clip_perna2)


        # ----------------------------------------------------------------------
        # PASSO 5: BRAÇOS (ACENO/BALANÇO)
        # ----------------------------------------------------------------------

        # BRAÇO ESQUERDO (Movimento de Aceno - Forte)
        if 'Braço Esquerdo' in parts:
            np_braco_esq = np.array(parts['Braço Esquerdo'].convert("RGBA"))
            clip_braco_esq = ImageClip(np_braco_esq, duration=clip_duration)
            
            def get_rotation_esq(t):
                # Aceno mais pronunciado
                return 20 * math.sin(2 * math.pi * t / clip_duration)  
            
            # Posicionamento no ombro esquerdo
            pos_braco_esq = get_rotated_pos(0, clip_braco_esq, OMBRO_ESQ_X_REL, OMBRO_Y_REL, get_rotation_esq)
            clip_braco_esq = clip_braco_esq.set_pos(pos_braco_esq)
            clip_braco_esq = clip_braco_esq.fx(lambda clip: clip.rotate(get_rotation_esq(clip.start), resample='bicubic'))
            final_clips.append(clip_braco_esq)


        # BRAÇO DIREITO (Balanço Suave - Fora de Fase com o esquerdo)
        if 'Braço Direito' in parts:
            np_braco_dir = np.array(parts['Braço Direito'].convert("RGBA"))
            clip_braco_dir = ImageClip(np_braco_dir, duration=clip_duration)
            
            def get_rotation_dir(t):
                # Balanço suave, fora de fase do braço esquerdo para evitar robotização
                return 10 * math.sin(2 * math.pi * t / clip_duration + math.pi / 2)  
                
            # Posicionamento no ombro direito
            pos_braco_dir = get_rotated_pos(0, clip_braco_dir, OMBRO_DIR_X_REL, OMBRO_Y_REL, get_rotation_dir)
            clip_braco_dir = clip_braco_dir.set_pos(pos_braco_dir)
            clip_braco_dir = clip_braco_dir.fx(lambda clip: clip.rotate(get_rotation_dir(clip.start), resample='bicubic'))
            final_clips.append(clip_braco_dir)
            
        # ----------------------------------------------------------------------
        # PASSO 6: CABEÇA, CABELO E OLHOS (Animação de "Vida")
        # ----------------------------------------------------------------------

        # FUNÇÕES GLOBAIS PARA CABEÇA E OLHOS
        def get_head_pos(t):
            # Balanço horizontal suave da cabeça (para simular inércia)
            x_offset = 3 * math.sin(2 * math.pi * SWAY_FREQ * t / 2)  
            y_offset = BREATH_AMP * math.sin(2 * math.pi * SWAY_FREQ * t) * 0.5 # metade da respiração do tronco
            return ('center', video_size[1]*0.15 + y_offset + BREATH_AMP) # Um pouco mais acima
            # Adicionei BREATH_AMP para que a cabeça comece um pouco mais alta e desça na respiração
            
        def get_head_rotation(t):
            # Rotação suave da cabeça (para compensar o tronco)
            return 1.0 * math.sin(2 * math.pi * SWAY_FREQ * t / 2)  
            
        
        # CABEÇA
        if 'Cabeça' in parts:
            np_cabeca = np.array(parts['Cabeça'].convert("RGBA"))
            clip_cabeca = ImageClip(np_cabeca, duration=clip_duration)
            
            clip_cabeca = clip_cabeca.set_position(get_head_pos)
            clip_cabeca = clip_cabeca.fx(lambda clip: clip.rotate(get_head_rotation(clip.start), resample='bicubic'))
            final_clips.append(clip_cabeca)
            
        # CABELO (Segue o movimento da cabeça, mas com um pouco mais de balanço/inércia)
        if 'Cabelo' in parts:
            np_cabelo = np.array(parts['Cabelo'].convert("RGBA"))
            clip_cabelo = ImageClip(np_cabelo, duration=clip_duration)
            
            clip_cabelo = clip_cabelo.set_position(get_head_pos)
            # Rotação ligeiramente mais exagerada para dar sensação
