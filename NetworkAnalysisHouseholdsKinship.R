#NetworkAnalysisHouseholdsKinship.R
#Author: M.V. Eitzel
#Created 2015-2016

# to test the relationship between inverse distance between households and the number of people the households had exchanged
# we used a Mantel test in the 'vegan' package.
# hhdist1 is the inverse cartesian distance, and hhproj1 is the projection which contains the number of people those two households had in common
# these are both 25x25 matrices (there were 25 unique households in our dataset over all years)
# we include households which had no location given (because they were very distance) by assigning the inverse distance to be zero
# note that we also did this test without those households and the results did not change appreciably.
# the 'r' statistic and p-value given in the main paper are for including those 'infintitely far' households.

library(vegan)
mantel(hhdist1, hhproj1, method="pearson", permutations=20000)

# to test the median pairwise network distance of a household against other predictor variables, we used the cumulative logit function
# in package 'ordinal'
# note that we tried the models with the wealth categorie as numeric and as categorical, and it was significant for neither of these choices
# similarly, because there were so few years in the dataset, we tried year as a category and as a centered numerical variable (cYear); this choice also did not change significance
# the anova command is used here to calculate the likelihood ratio test between the two models (one without the variable and one with)
# clmm is a mixed model with a random effect for household, and clm has no random effects

library(ordinal)

fit1<-clmm (as.factor(Median.Dist)~Size+as.factor(Year)+(1|Household.ID), data=hs)
fit2<-clmm (as.factor(Median.Dist)~Size+cYear+(1|Household.ID), data=hs)
#test whether the household is significant in and of itself when other variables are included (are some households more closely-connected)
fit1.HH<-clm(as.factor(Median.Dist)~Size+as.factor(Year), data=hs)
anova(fit1,fit1.HH) #0.1417
fit2.HH<-clm(as.factor(Median.Dist)~Size+cYear, data=hs)
anova(fit2,fit2.HH) #0.1969
# it's not

#test whether year is significant, whether a category or a continuous variable
fit1.yr<-clmm (as.factor(Median.Dist)~Size+(1|Household.ID), data=hs)
anova(fit1,fit1.yr) #0.01602
fit2.yr<-clmm(as.factor(Median.Dist)~Size+(1|Household.ID), data=hs)
anova(fit2,fit2.yr) #0.005612
#It is, regardless of whether it's category or continuous

#test whether household size determines median distance
fit1.sz<-clmm (as.factor(Median.Dist)~as.factor(Year)+(1|Household.ID), data=hs)
anova(fit1,fit1.sz) #0.001311
fit2.sz<-clmm(as.factor(Median.Dist)~cYear+(1|Household.ID), data=hs)
anova(fit2,fit2.sz) #0.0009313
# it does, regardless of how year is modeled

# to test the degree distributions of the household heads

fit.hh<-glm(Degree~IsHouseholdHead+Gender,family=poisson, data=HD)
#when I try quasipoisson, dispersion parameter is  1.169367 so close to poisson
anova(fit.hh,test="Chisq")
summary(fit.hh)

fit.hh.hh<-glm(Degree~Gender,family=poisson, data=HD)
anova(fit.hh,fit.hh.hh, test="Chisq")
fit.hh.g<-glm(Degree~IsHouseholdHead,family=poisson, data=HD)
anova(fit.hh,fit.hh.g,test="Chisq")


