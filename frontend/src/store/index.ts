import { configureStore, combineReducers } from '@reduxjs/toolkit'
import userReducer, { logout, loginStart, registerStart } from './slices/userSlice'
import paperReducer from './slices/paperSlice'
import favoritesReducer from './slices/favoritesSlice'

const appReducer = combineReducers({
  user: userReducer,
  paper: paperReducer,
  favorites: favoritesReducer
});

const rootReducer = (state, action) => {
  if (
    action.type === logout.type || 
    action.type === loginStart.type || 
    action.type === registerStart.type
  ) {
    // When a logout, new login, or new registration starts, reset the state
    state = undefined;
  }
  return appReducer(state, action);
};

export const store = configureStore({
  reducer: rootReducer
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch 