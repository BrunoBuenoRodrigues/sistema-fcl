import os
import time
import unittest
from pathlib import Path
from uuid import uuid4

os.environ["JWT_SECRET_KEY"] = "segredo-exclusivo-para-testes-integrados-fcl"

from app.armazenamento_arquivos import remover_arquivos_orfaos_expirados


class TestArmazenamentoArquivos(unittest.TestCase):
    def test_remove_somente_arquivo_gerado_orfao_e_expirado(self):
        agora = time.time()
        diretorio = Path(__file__).parent / "arquivos_teste"
        nomes = {
            "vinculado": f"{uuid4().hex}-vinculado.pdf",
            "orfao_expirado": f"{uuid4().hex}-orfao.pdf",
            "orfao_recente": f"{uuid4().hex}-recente.png",
            "legado": f"arquivo-legado-{uuid4().hex}.pdf",
        }

        try:
            for nome in nomes.values():
                (diretorio / nome).write_bytes(b"arquivo")

            idade_expirada = agora - (8 * 24 * 60 * 60)
            os.utime(diretorio / nomes["vinculado"], (idade_expirada,) * 2)
            os.utime(
                diretorio / nomes["orfao_expirado"],
                (idade_expirada,) * 2,
            )
            os.utime(diretorio / nomes["legado"], (idade_expirada,) * 2)

            removidos = remover_arquivos_orfaos_expirados(
                diretorio=diretorio,
                urls_vinculadas={
                    f"/arquivos/entregas/{nomes['vinculado']}"
                },
                retencao_horas=168,
                agora=agora,
            )

            self.assertEqual(removidos, [nomes["orfao_expirado"]])
            self.assertFalse((diretorio / nomes["orfao_expirado"]).exists())
            self.assertTrue((diretorio / nomes["vinculado"]).exists())
            self.assertTrue((diretorio / nomes["orfao_recente"]).exists())
            self.assertTrue((diretorio / nomes["legado"]).exists())
        finally:
            for nome in nomes.values():
                (diretorio / nome).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
