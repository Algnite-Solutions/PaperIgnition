import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface UserState {
  isRegistered: boolean
  isLoggedIn: boolean
  frequency: 'daily' | 'weekly'
  interests: {
    paperIds: string[]
    description: string
  }
  loading: boolean
  error: string | null
  selectedPapers: string[]
  isConfiguring: boolean
}

const initialState: UserState = {
  isRegistered: false,
  isLoggedIn: false,
  frequency: 'daily',
  interests: {
    paperIds: [],
    description: ''
  },
  loading: false,
  error: null,
  selectedPapers: [],
  isConfiguring: false
}

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    setFrequency: (state, action: PayloadAction<'daily' | 'weekly'>) => {
      state.frequency = action.payload
    },
    setInterests: (state, action: PayloadAction<{ paperIds: string[], description: string }>) => {
      state.interests = action.payload
    },
    setInterestDescription: (state, action: PayloadAction<string>) => {
      state.interests.description = action.payload
    },
    registerStart: (state) => {
      state.loading = true
      state.error = null
    },
    registerSuccess: (state) => {
      state.isRegistered = true
      state.loading = false
      state.error = null
    },
    registerFailure: (state, action: PayloadAction<string>) => {
      state.loading = false
      state.error = action.payload
    },
    loginStart: (state) => {
      state.loading = true
      state.error = null
    },
    loginSuccess: (state) => {
      state.isLoggedIn = true
      state.isRegistered = true
      state.loading = false
      state.error = null
    },
    loginFailure: (state, action: PayloadAction<string>) => {
      state.loading = false
      state.error = action.payload
    },
    logout: (state) => {
      state.isLoggedIn = false
    },
    startConfiguring: (state) => {
      state.isConfiguring = true
      state.error = null
    },
    togglePaperSelection: (state, action: PayloadAction<string>) => {
      const index = state.selectedPapers.indexOf(action.payload)
      if (index === -1) {
        state.selectedPapers.push(action.payload)
      } else {
        state.selectedPapers.splice(index, 1)
      }
    },
    setSelectedPapers: (state, action: PayloadAction<string[]>) => {
      state.selectedPapers = action.payload
    },
    saveInterestsStart: (state) => {
      state.loading = true
      state.error = null
    },
    saveInterestsSuccess: (state) => {
      state.interests.paperIds = state.selectedPapers
      state.loading = false
      state.isConfiguring = false
      state.error = null
    },
    saveInterestsWithDescription: (state, action: PayloadAction<string>) => {
      state.interests.description = action.payload
      state.interests.paperIds = state.selectedPapers
      state.loading = false
      state.isConfiguring = false
      state.error = null
    },
    saveInterestsFailure: (state, action: PayloadAction<string>) => {
      state.loading = false
      state.error = action.payload
    }
  }
})

export const {
  setFrequency,
  setInterests,
  setInterestDescription,
  registerStart,
  registerSuccess,
  registerFailure,
  loginStart,
  loginSuccess,
  loginFailure,
  logout,
  startConfiguring,
  togglePaperSelection,
  setSelectedPapers,
  saveInterestsStart,
  saveInterestsSuccess,
  saveInterestsWithDescription,
  saveInterestsFailure
} = userSlice.actions

export default userSlice.reducer 