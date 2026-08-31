# Test suite — captured output

**Date:** 2026-08-31 (re-captured; 78 tests on 2026-08-28, +4 since —
`test_una_cita_a_un_fragmento_inexistente_se_rechaza`,
`test_citar_nada_es_valido` and `test_el_modelo_ve_el_chunk_id_que_se_le_pide_citar`
from the fabricated-citations fix (`evidence/09`), plus
`test_fallo_del_gateway_escala_en_vez_de_crashear` from the gateway-failure fix
(`evidence/10`)) · `.venv/Scripts/python.exe -m pytest tests/ -v`

82 tests. None calls the model or reaches an external service except the
process-boundary test, which spawns real subprocesses on purpose: what it
checks is that state survives a process dying, and that cannot be mocked.

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- C:\Proyectos\AI\rgwallcovering-agent-ops\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Proyectos\AI\rgwallcovering-agent-ops
configfile: pytest.ini
plugins: anyio-4.14.2, langsmith-0.11.2, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 82 items

tests/test_async.py::test_el_bucle_decide_de_forma_asincrona PASSED      [  1%]
tests/test_async.py::test_la_herramienta_se_ejecuta_y_su_salida_vuelve_al_modelo PASSED [  2%]
tests/test_async.py::test_se_detiene_en_el_gate_sin_ejecutar_nada PASSED [  3%]
tests/test_async.py::test_aprobar_de_forma_asincrona_ejecuta_lo_aprobado PASSED [  5%]
tests/test_async.py::test_recuperacion_asincrona_con_el_motivo_exacto PASSED [  6%]
tests/test_async.py::test_agotar_el_presupuesto_escala_de_forma_asincrona PASSED [  7%]
tests/test_async.py::test_varios_leads_a_la_vez_no_se_mezclan PASSED     [  8%]
tests/test_corpus.py::test_falta_el_indice PASSED                        [ 10%]
tests/test_corpus.py::test_tier_ausente_rechaza_el_indice PASSED         [ 11%]
tests/test_corpus.py::test_tier_desconocido_rechaza_el_indice PASSED     [ 12%]
tests/test_corpus.py::test_indice_desalineado PASSED                     [ 14%]
tests/test_corpus.py::test_dimension_incorrecta PASSED                   [ 15%]
tests/test_corpus.py::test_json_invalido PASSED                          [ 16%]
tests/test_corpus.py::test_el_indice_heredado_carga PASSED               [ 17%]
tests/test_corpus.py::test_consulta_tematica_recupera_su_documento PASSED [ 19%]
tests/test_corpus.py::test_consulta_fuera_del_corpus_devuelve_vacio PASSED [ 20%]
tests/test_corpus.py::test_consulta_vacia PASSED                         [ 21%]
tests/test_corpus.py::test_tope_por_documento PASSED                     [ 23%]
tests/test_corpus.py::test_el_tier_sobrevive_a_la_recuperacion PASSED    [ 24%]
tests/test_corpus.py::test_top_k_invalido PASSED                         [ 25%]
tests/test_corpus.py::test_la_politica_de_la_visita_es_recuperable_en_nivel_a[is the assessment visit free] PASSED [ 26%]
tests/test_corpus.py::test_la_politica_de_la_visita_es_recuperable_en_nivel_a[is the assessment visit charged] PASSED [ 28%]
tests/test_corpus.py::test_la_politica_de_la_visita_es_recuperable_en_nivel_a[does the assessment fee depend on distance] PASSED [ 29%]
tests/test_corpus.py::test_la_politica_de_la_visita_es_recuperable_en_nivel_a[how much does the assessment visit cost] PASSED [ 30%]
tests/test_corpus.py::test_el_toponimo_hunde_la_politica PASSED          [ 32%]
tests/test_fallos.py::test_borrador_con_direccion_invalida_se_rechaza PASSED [ 33%]
tests/test_fallos.py::test_borrador_con_hueco_sin_rellenar_se_rechaza PASSED [ 34%]
tests/test_fallos.py::test_borrador_valido_pasa PASSED                   [ 35%]
tests/test_fallos.py::test_eventos_imposibles_se_rechazan[2026-09-05T09:00:00-04:00-2026-09-05T10:00:00-04:00-working day] PASSED [ 37%]
tests/test_fallos.py::test_eventos_imposibles_se_rechazan[2026-09-01T22:00:00-04:00-2026-09-01T23:00:00-04:00-working hours] PASSED [ 38%]
tests/test_fallos.py::test_eventos_imposibles_se_rechazan[2026-09-01T11:00:00-04:00-2026-09-01T10:00:00-04:00-ends before] PASSED [ 39%]
tests/test_fallos.py::test_eventos_imposibles_se_rechazan[2026-09-01T08:00:00-2026-09-01T09:00:00-no timezone] PASSED [ 41%]
tests/test_fallos.py::test_el_motivo_sirve_para_corregir_no_solo_para_diagnosticar PASSED [ 42%]
tests/test_fallos.py::test_el_reintento_lleva_el_motivo_exacto PASSED    [ 43%]
tests/test_fallos.py::test_nada_llego_al_cliente_se_dice_en_el_reintento PASSED [ 44%]
tests/test_fallos.py::test_agotar_el_presupuesto_escala_en_vez_de_girar PASSED [ 43%]
tests/test_fallos.py::test_fallo_del_gateway_escala_en_vez_de_crashear PASSED [ 45%]
tests/test_fallos.py::test_la_escalacion_lleva_todos_los_motivos_no_el_ultimo PASSED [ 46%]
tests/test_fallos.py::test_la_escalacion_dice_que_no_se_envio_nada PASSED [ 47%]
tests/test_fallos.py::test_la_escalacion_sin_canal_lo_dice PASSED        [ 48%]
tests/test_fallos.py::test_la_escalacion_solo_cita_fuentes_que_respaldan PASSED [ 50%]
tests/test_fallos.py::test_la_inyeccion_esta_apagada_por_defecto PASSED  [ 51%]
tests/test_fallos.py::test_la_inyeccion_falla_solo_las_veces_pedidas PASSED [ 52%]
tests/test_fallos.py::test_el_motivo_inyectado_se_declara_como_tal PASSED [ 53%]
tests/test_fallos.py::test_el_reintento_dice_donde_fallo_no_solo_que_fallo PASSED [ 54%]
tests/test_fallos.py::test_una_cita_a_un_fragmento_inexistente_se_rechaza PASSED [ 56%]
tests/test_fallos.py::test_citar_nada_es_valido PASSED                   [ 57%]
tests/test_fallos.py::test_el_modelo_ve_el_chunk_id_que_se_le_pide_citar PASSED [ 58%]
tests/test_gate.py::test_ejecutar_irreversible_tiene_exactamente_una_arista_de_entrada PASSED [ 59%]
tests/test_gate.py::test_ningun_nodo_salvo_el_gate_alcanza_el_envio PASSED [ 60%]
tests/test_gate.py::test_el_nodo_irreversible_se_niega_sin_aprobacion PASSED [ 62%]
tests/test_gate.py::test_el_grafo_se_detiene_en_el_gate_y_muestra_la_propuesta PASSED [ 63%]
tests/test_gate.py::test_aprobar_ejecuta_y_deja_registro PASSED          [ 64%]
tests/test_gate.py::test_rechazar_no_envia_y_realimenta_el_motivo PASSED [ 65%]
tests/test_gate.py::test_lo_editado_es_lo_que_se_ejecuta PASSED          [ 67%]
tests/test_gate.py::test_direcciones_invalidas_se_rechazan_antes_de_conectar[] PASSED [ 68%]
tests/test_gate.py::test_direcciones_invalidas_se_rechazan_antes_de_conectar[   ] PASSED [ 69%]
tests/test_gate.py::test_direcciones_invalidas_se_rechazan_antes_de_conectar[j.torres@gmailcom] PASSED [ 70%]
tests/test_gate.py::test_direcciones_invalidas_se_rechazan_antes_de_conectar[sin-arroba] PASSED [ 71%]
tests/test_gate.py::test_direcciones_invalidas_se_rechazan_antes_de_conectar[a@b] PASSED [ 73%]
tests/test_gate.py::test_el_motivo_del_rechazo_dice_por_que_no_se_corrige PASSED [ 74%]
tests/test_gate.py::test_cuerpo_vacio_no_se_envia PASSED                 [ 75%]
tests/test_gate.py::test_la_decision_deja_el_historial_bien_formado PASSED [ 76%]
tests/test_grafo.py::test_decide_sin_buscar_cuando_no_hace_falta PASSED  [ 78%]
tests/test_grafo.py::test_busca_y_luego_decide PASSED                    [ 79%]
tests/test_grafo.py::test_la_prosa_suelta_no_cuenta_como_decision PASSED [ 80%]
tests/test_grafo.py::test_el_tope_de_llamadas_escala_en_vez_de_gastar PASSED [ 81%]
tests/test_grafo.py::test_la_traza_registra_la_decision_y_su_motivo PASSED [ 82%]
tests/test_grafo.py::test_las_etiquetas_no_entran_en_el_estado PASSED    [ 84%]
tests/test_memoria.py::test_la_aprobacion_sobrevive_a_la_muerte_del_proceso PASSED [ 85%]
tests/test_memoria.py::test_un_hilo_desconocido_no_ejecuta_nada PASSED   [ 86%]
tests/test_memoria.py::test_el_ledger_acumula_y_no_reescribe PASSED      [ 87%]
tests/test_memoria.py::test_los_intentos_fallidos_se_cuentan_entre_sesiones PASSED [ 89%]
tests/test_memoria.py::test_una_linea_corrupta_no_impide_leer_las_demas PASSED [ 90%]
tests/test_memoria.py::test_el_ledger_no_guarda_el_cuerpo_del_correo PASSED [ 91%]
tests/test_memoria.py::test_los_tipos_del_estado_estan_declarados_para_serializar PASSED [ 92%]
tests/test_tools.py::test_esquema_dice_cuando_no_llamar PASSED           [ 93%]
tests/test_tools.py::test_esquema_ensena_a_desconfiar_del_registro PASSED [ 95%]
tests/test_tools.py::test_sin_pasajes_no_invita_a_rellenar PASSED        [ 96%]
tests/test_tools.py::test_los_pasajes_llevan_su_tier_delante PASSED      [ 97%]
tests/test_tools.py::test_la_salida_se_declara_como_dato PASSED          [ 98%]
tests/test_tools.py::test_herramienta_desconocida PASSED                 [100%]

============================= 82 passed in 14.79s =============================
```
