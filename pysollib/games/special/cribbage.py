#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# ---------------------------------------------------------------------------##
#
# Copyright (C) 1998-2003 Markus Franz Xaver Johannes Oberhumer
# Copyright (C) 2003 Mt. Hood Playing Card Co.
# Copyright (C) 2005-2009 Skomoroh
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ---------------------------------------------------------------------------##


from pysollib.game import Game
from pysollib.gamedb import GI, GameInfo, registerGame
from pysollib.layout import Layout
from pysollib.mygettext import _
from pysollib.pysoltk import MfxCanvasText
from pysollib.stack import \
        InitialDealTalonStack, \
        InvisibleStack, \
        OpenTalonStack, \
        ReserveStack, \
        StackWrapper

# ************************************************************************
# * Cribbage Square
# ************************************************************************


class CribbageSquare_RowStack(ReserveStack):
    def clickHandler(self, event):
        if not self.cards:
            self.game.s.talon.playMoveMove(1, self)
            return 1
        return ReserveStack.clickHandler(self, event)

    rightclickHandler = clickHandler


class CribbageSquare_Talon(OpenTalonStack):
    def canMoveCards(self, cards):
        if self.game.isBoardFull():
            return False
        return OpenTalonStack.canMoveCards(self, cards)


class CribbageSquare(Game):
    Talon_Class = CribbageSquare_Talon
    RowStack_Class = StackWrapper(CribbageSquare_RowStack, max_move=0)
    Hint_Class = None

    WIN_SCORE = 61
    NUM_RESERVE = 0
    RESERVE_STACK = StackWrapper(ReserveStack, max_cards=5)

    #
    # game layout
    #

    def createGame(self):
        # create layout
        l, s = Layout(self), self.s

        # create texts 1)
        ta = "ss"
        x, y = l.XM, l.YM + 2 * l.YS

        # set window
        w = max(2 * l.XS, x, ((self.NUM_RESERVE + 1) * l.XS) + (4 * l.XM))
        self.setSize(l.XM + w + 4 * l.XS + 50, l.YM + 4 * l.YS + 30)

        # create stacks
        for i in range(4):
            for j in range(4):
                x, y = l.XM + w + j * l.XS, l.YM + i * l.YS
                s.rows.append(self.RowStack_Class(x, y, self))
        x, y = l.XM, l.YM
        s.talon = self.Talon_Class(x, y, self)
        l.createText(s.talon, anchor=ta)
        s.internals.append(InvisibleStack(self))    # for _swapPairMove()

        for i in range(self.NUM_RESERVE):
            x, y = ((i + 1) * l.XS) + (2 * l.XM), l.YM
            s.reserves.append(self.RESERVE_STACK(x, y, self))

        # create texts 2)
        if self.preview <= 1:
            for i in (3, 7, 11, 15):
                tx, ty, ta, tf = l.getTextAttr(s.rows[i], anchor="e")
                t = MfxCanvasText(self.canvas, tx + 8, ty,
                                  anchor=ta,
                                  font=self.app.getFont("canvas_default"))
                self.texts.list.append(t)
            for i in range(12, 16):
                tx, ty, ta, tf = l.getTextAttr(s.rows[i], anchor="ss")
                t = MfxCanvasText(self.canvas, tx, ty, anchor=ta,
                                  font=self.app.getFont("canvas_default"))
                self.texts.list.append(t)
            self.texts.score = MfxCanvasText(
                self.canvas, l.XM, 4 * l.YS, anchor="sw",
                font=self.app.getFont("canvas_large"))

        # define hands for scoring
        r = s.rows
        self.cribbage_hands = [
            r[0:4],  r[4:8], r[8:12], r[12:16],
            (r[0], r[0+4], r[0+8], r[0+12]),
            (r[1], r[1+4], r[1+8], r[1+12]),
            (r[2], r[2+4], r[2+8], r[2+12]),
            (r[3], r[3+4], r[3+8], r[3+12])
        ]
        self.cribbage_hands = list(map(tuple, self.cribbage_hands))

        # define stack-groups
        l.defaultStackGroups()
        return l

    #
    # game overrides
    #

    def startGame(self):
        self.moveMove(35 - (5 * self.NUM_RESERVE), self.s.talon,
                      self.s.internals[0], frames=0)
        self.s.talon.fillStack()

    def isBoardFull(self):
        for i in range(16):
            if len(self.s.rows[i].cards) == 0:
                return False
        return True

    def isGameWon(self):
        if self.isBoardFull():
            return self.getGameScore() >= self.WIN_SCORE

        return False

    def getAutoStacks(self, event=None):
        return ((), (), ())

    #
    # scoring
    #

    def updateText(self):
        if self.preview > 1:
            return
        score = 0
        for i in range(8):
            value = self.getHandScore(self.cribbage_hands[i])

            self.texts.list[i].config(text=str(value))
            score += value
        #
        score = self.checkHisHeels(score)
        t = ""
        if score >= self.WIN_SCORE:
            t = _("WON\n\n")
        if not self.isBoardFull():
            t += _("Points: %d") % score
        else:
            t += _("Total: %d") % score
        self.texts.score.config(text=t)

    def getGameScore(self):
        score = 0
        for hand in self.cribbage_hands:
            value = self.getHandScore(hand)
            score += value

        score = self.checkHisHeels(score)
        return score

    def getAllCombinations(self, hand):
        if hand == ():
            return ((),)

        x = self.getAllCombinations(hand[1:])

        return x + tuple([(hand[0],) + y for y in x])

    def getHandScore(self, hand):
        same_suit = [0] * 4
        hand_score = 0

        upcard = None
        upcard_talon = None
        if self.isBoardFull():
            upcard = self.s.talon.cards[0]
            upcard_talon = self.s.talon

        # First get flushes and his nobs, as these can only be
        # scored once per hand.
        for s in hand:
            if s.cards:
                suit = s.cards[0].suit
                same_suit[suit] = same_suit[suit] + 1
                if upcard is not None and s.cards[0].rank == 10 \
                        and s.cards[0].suit == upcard.suit:
                    hand_score += 1  # His nobs
        #
        if max(same_suit) == 4:
            hand_score += 4  # Flush
            if upcard is not None and upcard.suit == hand[0].cards[0].suit:
                hand_score += 1  # Flush of five

        if upcard is not None:
            hand = hand + (upcard_talon,)
        combos = self.getAllCombinations(hand)

        longest_run = 3
        run_score = 0
        # The remaining hands can be scored for every combination.
        for c in combos:
            c_same_rank = [0] * 13
            c_ranks = []
            total = 0
            incomplete = False

            for s in c:
                if s.cards:
                    rank = s.cards[0].rank
                    c_same_rank[rank] = c_same_rank[rank] + 1
                    c_ranks.append(rank)

                    if rank < 10:
                        total += (rank + 1)
                    else:
                        total += 10
                else:
                    incomplete = True
                    break

            if incomplete:
                continue

            if total == 15:
                hand_score += 2  # Fifteen

            if len(c) == 2 and max(c_same_rank) == 2:
                hand_score += 2  # Pair

            # For runs, we only want to consider the longest run
            if len(c) >= longest_run:
                if c_same_rank.count(1) == len(c):
                    d = max(c_ranks) - min(c_ranks)
                    if d == len(c) - 1:
                        if len(c) > longest_run:
                            run_score = 0
                            longest_run = len(c)
                        run_score += longest_run  # Runs

        hand_score += run_score

        return hand_score

    def checkHisHeels(self, score):
        if self.isBoardFull() and self.s.talon.cards[0].rank == 10:
            return score + 2
        return score


# ************************************************************************
# * Cribbage Shuffle
# ************************************************************************

class CribbageShuffle_RowStack(ReserveStack):
    def moveMove(self, ncards, to_stack, frames=-1, shadow=-1):
        assert ncards == 1 and to_stack in self.game.s.rows
        assert len(to_stack.cards) == 1
        self._swapPairMove(ncards, to_stack, frames=-1, shadow=0)

    def _swapPairMove(self, n, other_stack, frames=-1, shadow=-1):
        game = self.game
        old_state = game.enterState(game.S_FILL)
        swap = game.s.internals[0]
        game.moveMove(n, self, swap, frames=0)
        game.moveMove(n, other_stack, self, frames=frames, shadow=shadow)
        game.moveMove(n, swap, other_stack, frames=0)
        game.leaveState(old_state)


class CribbageShuffle(CribbageSquare):
    Talon_Class = InitialDealTalonStack
    RowStack_Class = StackWrapper(
        CribbageShuffle_RowStack, max_accept=1, max_cards=2)

    WIN_SCORE = 61

    def createGame(self):
        CribbageSquare.createGame(self)
        if self.s.talon.texts.ncards:
            self.s.talon.texts.ncards.text_format = "%D"

    def startGame(self):
        self.moveMove(35, self.s.talon, self.s.internals[0], frames=0)
        self._startAndDealRow()
        self.s.talon.flipMove()


# ************************************************************************
# * Cribbage Square (Waste)
# * Cribbage Square (1 Reserve)
# * Cribbage Square (2 Reserves)
# ************************************************************************

class CribbageSquareWaste(CribbageSquare):
    NUM_RESERVE = 1
    RESERVE_STACK = StackWrapper(ReserveStack, max_cards=5, max_move=0)


class CribbageSquare1Reserve(CribbageSquare):
    NUM_RESERVE = 1


class CribbageSquare2Reserves(CribbageSquare):
    NUM_RESERVE = 2


# register the game
registerGame(GameInfo(805, CribbageSquare, "Cribbage Square",
                      GI.GT_CRIBBAGE_TYPE | GI.GT_SCORE, 1, 0,
                      GI.SL_MOSTLY_SKILL, si={"ncards": 17}))
registerGame(GameInfo(806, CribbageSquareWaste, "Cribbage Square (Waste)",
                      GI.GT_CRIBBAGE_TYPE | GI.GT_SCORE, 1, 0,
                      GI.SL_MOSTLY_SKILL, si={"ncards": 22},
                      rules_filename="cribbagesquare.html"))
registerGame(GameInfo(807, CribbageSquare1Reserve,
                      "Cribbage Square (1 Reserve)",
                      GI.GT_CRIBBAGE_TYPE | GI.GT_SCORE, 1, 0,
                      GI.SL_MOSTLY_SKILL, si={"ncards": 22},
                      rules_filename="cribbagesquare.html"))
registerGame(GameInfo(808, CribbageSquare2Reserves,
                      "Cribbage Square (2 Reserves)",
                      GI.GT_CRIBBAGE_TYPE | GI.GT_SCORE, 1, 0,
                      GI.SL_MOSTLY_SKILL, si={"ncards": 27},
                      rules_filename="cribbagesquare.html"))
registerGame(GameInfo(809, CribbageShuffle, "Cribbage Shuffle",
                      GI.GT_CRIBBAGE_TYPE | GI.GT_SCORE | GI.GT_OPEN, 1, 0,
                      GI.SL_MOSTLY_SKILL,
                      si={"ncards": 17}))
