class pick_score_up(dst_stocks):

    def filter(self, context, data, dst_stocks):
        stock_list = get_index_stocks('000001.XSHG')
        dst_stocks = {}
        for stock in stock_list:
            h = attribute_history(stock, 130, unit='1d', fields=('close', 'high', 'low'), skip_paused=True)
            low_price_130 = h.low.min()
            high_price_130 = h.high.max()

            avg_15 = data[stock].mavg(15, field='close')
            cur_price = data[stock].close

            score = (cur_price - low_price_130) + (cur_price - high_price_130) + (cur_price - avg_15)
            if score >= 10:
                dst_stocks.append(stock)

        return list(dst_stocks)

    def __str__(self):
        return '股票评分 [评分股数: %d ]' % (self.dst_stocks)

