import logging
import time
import sys
from JoycontrolPlugin import JoycontrolPlugin, JoycontrolPluginError
from pathlib import Path

sys.path.append(str(Path().cwd().parent / 'common'))
from CustomCommon import CustomCommon

logger = logging.getLogger(__name__)
# 新しいキャプチャ画像を取得するための試行回数
CAP_PREPARE = 10
# 孵化したポケモンのチェック周期 1-5で設定
CHECK_CYCLE = 5

class HatchEggsOCR(CustomCommon):
    def __init__(self, controller_state, options):
        super().__init__(controller_state, options)
        if options is None or len(options) < 4:
            raise JoycontrolPluginError('4つのオプションを指定してください ex "-p 孵化試行回数 個体値リスト 特性確認 色違い確認"')
        self.total_eggs = int(options[0])
        if self.total_eggs > 1000:
            raise JoycontrolPluginError('孵化試行回数は 1000 までの範囲で指定してください。')
        self.iv_check_list = options[1].split('-')
        if len(self.iv_check_list) != 6:
            raise JoycontrolPluginError('個体値リストは v-x-v-v-v-0 のように指定してください。')
        for param in self.iv_check_list:
            if param not in ['v', '0', 'x']:
                raise JoycontrolPluginError('個体値は v 0 x のいずれかを指定してください。v=さいこう, 0=ダメかも, x=チェックしない')
        self.ability_check = options[2]
        if not len(self.ability_check) < 10:
            raise JoycontrolPluginError('特性は10文字未満で指定してください。または any と指定すればチェックしません')
        self.shiny_check_div = options[3]
        if self.shiny_check_div not in ['want', 'must', 'any']:
            raise JoycontrolPluginError('色違いは want must any のいずれかを指定してください。want=他条件とOR, must=他条件とAND, any=チェックしない')
        self.hatch_msg = self.get_threshhold_img('hatch_msg.jpg')
        self.shiny_mark = self.get_threshhold_img('shiny_mark.jpg')
        self.is_finish = False

    async def use_flying_taxi(self):
        # メニューを開く
        await self.button_ctl('x')
        # 左下のタウンマップを開く
        await self.button_ctl('up', 'left', p_sec=1.0)
        await self.button_ctl('down', w_sec=0.5)
        await self.button_ctl('a', w_sec=3.0)
        # 自分のいるエリアにそらとぶタクシー
        await self.button_ctl('a', w_sec=0.8)
        await self.button_ctl('a', w_sec=3.0)

    async def get_egg(self):
        # 預かり屋の前まで移動
        await self.left_stick('down', power=1100)
        await self.wait(1.8)
        await self.left_stick('right')
        await self.wait(0.3)
        await self.left_stick('center')
        # タマゴを受け取る
        await self.button_ctl('a', w_sec=0.8)
        await self.button_ctl('a', w_sec=0.8)
        await self.button_ctl('down', w_sec=0.1)
        await self.button_ctl('down', w_sec=0.1)
        await self.button_ctl('a')
        # B連打
        for _ in range(55):
            await self.button_ctl('b')

    async def hatch_egg(self):
        # 預かり屋の近くでグルグル移動
        await self.left_stick(angle=145)
        await self.wait(1.5)
        await self.left_stick('left')
        await self.right_stick('right')
        await self.wait(1.0)
        # キャプチャ読み込みを何度か実施
        for _ in range(CAP_PREPARE):
            ret, frame = self.cap.read()
        # 画像処理でうまく判断できない場合のリミットは3分(180秒)
        limit_time = time.time() + 180
        while time.time() < limit_time:
            # キャプチャ画像を取得
            ret, frame = self.cap.read()
            # 「おや……？」の画像と一致するまで処理をループ
            thresh_img = await self.get_thresh_img(frame, 400, 880, 280, 80)
            ret, is_match = await self.check_nonzero(self.hatch_msg, thresh_img, 22000)
            if is_match:
                break
        msg = '画像処理で孵化を確認' if time.time() < limit_time else '時間超過のため処理中断'
        logger.info(msg)
        await self.left_stick('center')
        await self.right_stick('center')
        # B連打
        for _ in range(160):
            await self.button_ctl('b')

    async def check_pokemon(self):
        logger.info('チェック処理開始')
        await self.open_pokemon_box() # ボックスを開く
        # 手持ちの2番目に移動
        await self.button_ctl('left', p_sec=0.2, w_sec=0.1)
        await self.button_ctl('down', w_sec=0.1)
        for _ in range(CHECK_CYCLE):
            # キャプチャ読み込みを何度か実施
            for _ in range(CAP_PREPARE):
                ret, frame = self.cap.read()
            thresh_img = await self.get_thresh_img(frame, 1760, 30, 160, 60)
            ocr_text = await self.get_ocr_text(thresh_img)
            # OCRをかけた結果右上のレベルが見えなければ中断
            if ocr_text == '':
                logger.info('手持ちがいないため処理を中断します。')
                break
            is_shiny = await self.check_shiny(frame)
            # want指定で色違いを発見した場合は優先的に完了する
            if is_shiny and self.shiny_check_div == 'want':
                self.is_finish = True
                break
            is_target = True
            is_target &= await self.check_iv(frame)
            is_target &= await self.check_ability(frame)
            is_shiny = is_shiny and self.shiny_check_div == 'must'
            is_shiny |= self.shiny_check_div != 'must'
            # 指定した条件に一致したら中断する
            if is_target and is_shiny:
                self.is_finish = True
                break
            await self.wait(0.5)
            # ターゲットではないので逃がす
            await self.button_ctl('a', p_sec=0.1, w_sec=0.5)
            await self.button_ctl('up', w_sec=0.3)
            await self.button_ctl('up', w_sec=0.3)
            await self.button_ctl('a', w_sec=1.0)
            await self.button_ctl('up', w_sec=0.3)
            await self.button_ctl('a', p_sec=0.1, w_sec=1.5)
            await self.button_ctl('a', p_sec=0.1)
            logger.info('条件に一致しないためポケモンを逃がしました。')
            await self.wait(0.1)
        # B連打
        for _ in range(35):
            await self.button_ctl('b')
        logger.info('チェック処理終了')

    async def check_iv(self, frame):
        # 個体値指定の判定
        ret_flg = True
        for i, check_type in enumerate(self.iv_check_list):
            # x であればスキップ
            if check_type == 'x':
                continue
            # v なら「さいこう」 0 なら「ダメかも」を比較対象にする
            iv = 'さいこう' if check_type == 'v' else 'ダメかも'
            # frameから画像を切り出してOCRをかける
            thresh_img = await self.get_thresh_img(frame, 1490, 215 + 56 * i, 170, 56)
            ocr_text = await self.get_ocr_text(thresh_img)
            # 文字比較をして類似度をチェック
            ret, is_match = await self.words_match(iv, ocr_text)
            logger.info('cursor={},input={},ocr={},ret={}'.format(i, iv, ocr_text, ret))
            # 1つでも不一致があればFalse返却とする
            ret_flg &= is_match
        return ret_flg

    async def check_ability(self, frame):
        # any であればスキップ
        if self.ability_check == 'any':
            return True
        # frameから画像を切り出してOCRをかける
        thresh_img = await self.get_thresh_img(frame, 1490, 215 + 56 * 7, 270, 56)
        ocr_text = await self.get_ocr_text(thresh_img)
        # 文字比較をして類似度をチェック
        ret, is_match = await self.words_match(self.ability_check, ocr_text)
        logger.info('input={},ocr={},ret={}'.format(self.ability_check, ocr_text, ret))
        return is_match

    async def check_shiny(self, frame):
        # any であれば確認しないで True を返却
        if self.shiny_check_div == 'any':
            return True
        # frameから画像を切り出して画像比較する
        thresh_img = await self.get_thresh_img(frame, 1860, 160, 50, 50)
        ret, is_shiny = await self.check_nonzero(self.shiny_mark, thresh_img, 2400)
        logger.info('ret={}'.format(ret))
        return is_shiny

    async def run(self):
        logger.info('プラグイン実行開始')
        egg_count = 0
        # setup_videoを有効にしている場合は映像が安定するまで待機
        wait_time = 9.0 if hasattr(self, 'cap') else 0.5
        await self.wait(wait_time)
        for _ in range(self.total_eggs):
            # 完了フラグが有効であれば処理を中断
            if self.is_finish:
                break
            await self.use_flying_taxi() # そらとぶタクシーで位置リセット
            await self.get_egg() # タマゴ獲得
            egg_count += 1
            logger.info('{}/{} 孵化作業開始'.format(egg_count, self.total_eggs))
            await self.hatch_egg() # 孵化作業
            logger.info('{}/{} 孵化作業完了'.format(egg_count, self.total_eggs))
            if egg_count % CHECK_CYCLE == 0:
                await self.check_pokemon() # 孵化したポケモンのステータスチェック
                await self.wait(1.0)
        if egg_count % CHECK_CYCLE != 0:
            await self.check_pokemon() # 孵化したポケモンのステータスチェック
        finish_msg = '発見したので完了します。' if self.is_finish else '該当は見つかりませんでした。'
        await self.send_slack_message(finish_msg)
        logger.info('結果 : {}'.format(finish_msg))
        logger.info('プラグイン実行終了')
